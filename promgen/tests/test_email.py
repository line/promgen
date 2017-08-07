# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

from unittest import mock

from django.test import override_settings
from django.urls import reverse

from promgen import models
from promgen.notification.email import NotificationEmail
from promgen.tests import PromgenTest


TEST_SETTINGS = PromgenTest.data_yaml('promgen.yml')
TEST_ALERT = PromgenTest.data('alertmanager.json')


class EmailTest(PromgenTest):
    @mock.patch('django.db.models.signals.post_save', mock.Mock())
    def setUp(self):
        self.shard = models.Shard.objects.create(name='Shard 1')
        self.service = models.Service.objects.create(name='Service 1', shard=self.shard)
        self.project = models.Project.objects.create(name='Project 1', service=self.service)
        self.project2 = models.Project.objects.create(name='Project 2', service=self.service)
        self.sender = models.Sender.create(
            obj=self.project,
            sender=NotificationEmail.__module__,
            value='example@example.com',
        )
        models.Sender.create(
            obj=self.project,
            sender=NotificationEmail.__module__,
            value='foo@example.com',
        )
        models.Sender.create(
            obj=self.project2,
            sender=NotificationEmail.__module__,
            value='bar@example.com',
        )

    @override_settings(PROMGEN=TEST_SETTINGS)
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @mock.patch('promgen.notification.email.send_mail')
    def test_email(self, mock_email):
        self.client.post(reverse('alert'),
            data=TEST_ALERT,
            content_type='application/json'
        )

        with open('promgen/tests/notifications/email.subject.txt') as fp:
            _SUBJECT = fp.read().strip()
        with open('promgen/tests/notifications/email.body.txt') as fp:
            _MESSAGE = fp.read().strip()

        mock_email.assert_has_calls([
            mock.call(
                _SUBJECT,
                _MESSAGE.format(service=self.service, project=self.project),
                'promgen@example.com',
                ['example@example.com']
            ),
            mock.call(
                _SUBJECT,
                _MESSAGE.format(service=self.service, project=self.project),
                'promgen@example.com',
                ['foo@example.com']
            )
        ])
        # Three senders are registered but only two should trigger
        self.assertTrue(mock_email.call_count == 2)
