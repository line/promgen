# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import json
from unittest import mock

from django.test import TestCase, override_settings
from django.urls import reverse

from promgen import models
from promgen.notification.ikasan import NotificationIkasan
from promgen.tests import PromgenTest

TEST_SETTINGS = PromgenTest.data_yaml('examples', 'promgen.yml')
TEST_ALERT = PromgenTest.data('examples', 'alertmanager.json')


class IkasanTest(TestCase):
    @mock.patch('django.dispatch.dispatcher.Signal.send')
    def setUp(self, mock_signal):
        self.shard = models.Shard.objects.create(name='test.shard')
        self.service = models.Service.objects.create(name='test.service', shard=self.shard)
        self.project = models.Project.objects.create(name='test.project', service=self.service)
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
            data=TEST_ALERT,
            content_type='application/json'
        )

        # Swap the status to test our resolved alert
        SAMPLE = PromgenTest.data_json('examples', 'alertmanager.json')
        SAMPLE['status'] = 'resolved'
        self.client.post(reverse('alert'),
            data=json.dumps(SAMPLE),
            content_type='application/json'
        )

        _MESSAGE = PromgenTest.data('notifications', 'ikasan.body.txt').strip()
        _RESOLVED = PromgenTest.data('notifications', 'ikasan.resolved.txt').strip()

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
