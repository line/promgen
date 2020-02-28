# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import json
from unittest import mock

from django.test import override_settings
from django.urls import reverse

from promgen import models, tests
from promgen.notification.ikasan import NotificationIkasan

TEST_SETTINGS = tests.Data('examples', 'promgen.yml').yaml()
TEST_ALERT = tests.Data('examples', 'alertmanager.json').yaml()


class IkasanTest(tests.PromgenTest):
    @mock.patch('django.dispatch.dispatcher.Signal.send')
    def setUp(self, mock_signal):
        self.shard = models.Shard.objects.create(name='test.shard')
        self.service = models.Service.objects.create(name='test.service')
        self.project = models.Project.objects.create(name='test.project', service=self.service, shard=self.shard)
        self.sender = models.Sender.objects.create(
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
        SAMPLE = tests.Data('examples', 'alertmanager.json').json()
        SAMPLE['status'] = 'resolved'
        self.client.post(reverse('alert'),
            data=json.dumps(SAMPLE),
            content_type='application/json'
        )

        _MESSAGE = tests.Data('notification', 'ikasan.body.txt').raw().strip()
        _RESOLVED = tests.Data('notification', 'ikasan.resolved.txt').raw().strip()

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
