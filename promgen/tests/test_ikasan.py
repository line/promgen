# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import json
from unittest import mock

from django.test import TestCase, override_settings
from django.urls import reverse

from promgen import models
from promgen.notification.ikasan import NotificationIkasan
from promgen.tests import TEST_ALERT, TEST_SETTINGS


_RESOLVED = '[resolved] service_level_alert Service 2 critical'
_MESSAGE = '''[firing] node_down prod foo-BETA testhost.localhost:9100 node Project 1 Service 1 critical

description: testhost.localhost:9100 of job node has been down for more than 5 minutes.
project: http://example.com/project/{project.id}/
service: http://example.com/service/{service.id}/
summary: Instance testhost.localhost:9100 down

Prometheus: https://monitoring.promehteus.localhost/graph#%5B%7B%22expr%22%3A%22up%20%3D%3D%200%22%2C%22tab%22%3A0%7D%5D'''


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
        self.service2 = models.Service.objects.create(name='Service 2', shard=self.shard)
        self.sender2 = models.Sender.create(
            obj=self.service2,
            sender=NotificationIkasan.__module__,
            value='#2',
        )

    @override_settings(PROMGEN=TEST_SETTINGS)
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @mock.patch('promgen.util.post')
    def test_ikasan(self, mock_post):
        self.client.post(reverse('alert'),
            data=json.dumps(TEST_ALERT),
            content_type='application/json'
        )
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
                'channel': '#2',
                'message_format': 'text',
                'message': _RESOLVED}
            ),
        ], any_order=True)
