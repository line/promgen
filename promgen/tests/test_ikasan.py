# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import json
from unittest import mock

from django.test import TestCase, override_settings
from django.urls import reverse

from promgen import models
from promgen.notification.ikasan import NotificationIkasan
from promgen.tests import TEST_ALERT, TEST_SETTINGS


class IkasanTest(TestCase):
    @mock.patch('django.db.models.signals.post_save', mock.Mock())
    def setUp(self):
        self.shard = models.Shard.objects.create(name='Shard 1')
        self.service = models.Service.objects.create(name='Service 1', shard=self.shard)
        self.project = models.Project.objects.create(name='Project 1', service=self.service)
        self.sender = models.Sender.create(
            obj=self.project,
            sender=NotificationIkasan.__module__,
            value='#1',
        )

    @override_settings(PROMGEN=TEST_SETTINGS)
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @mock.patch('promgen.util.post')
    def test_ikasan(self, mock_post):
        self.client.post(reverse('alert'),
            data=json.dumps(TEST_ALERT),
            content_type='application/json'
        )

        # Swap the status to test our resolved alert
        TEST_ALERT['status'] = 'resolved'
        self.client.post(reverse('alert'),
            data=json.dumps(TEST_ALERT),
            content_type='application/json'
        )

        with open('promgen/tests/notifications/ikasan.body.txt') as fp:
            _MESSAGE = fp.read().strip()
        with open('promgen/tests/notifications/ikasan.resolved.txt') as fp:
            _RESOLVED = fp.read().strip()

        mock_post.assert_has_calls([
            mock.call(
                'http://ikasan.example', {
                'color': 'red',
                'channel': '#1',
                'message_format': 'text',
                'message': _MESSAGE.format(service=self.service, project=self.project)}
            ),
            mock.call(
                'http://ikasan.example', {
                'color': 'green',
                'channel': '#1',
                'message_format': 'text',
                'message': _RESOLVED}
            ),
        ], any_order=True)
