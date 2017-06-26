# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import json
from unittest import mock

from django.test import TestCase, override_settings
from django.urls import reverse

from promgen import models
from promgen.notification.webhook import NotificationWebhook
from promgen.tests import TEST_ALERT, TEST_SETTINGS

_PARAM1 = {
    'externalURL': 'https://am.promehteus.localhost',
    'alert': {
        'labels': {
            'severity': 'critical',
            'env': 'prod',
            'service': 'Service 1',
            'project': 'Project 1',
            'alertname': 'node_down',
            'instance': 'testhost.localhost:9100',
            'job': 'node',
            'farm': 'foo-BETA'
        },
        'annotations': {
            'service': 'http://example.com/service/{service.id}/',
            'description': 'testhost.localhost:9100 of job node has been down for more than 5 minutes.',
            'summary': 'Instance testhost.localhost:9100 down',
            'project': 'http://example.com/project/{project.id}/'
        },
        'generatorURL': 'https://monitoring.promehteus.localhost/graph#%5B%7B%22expr%22%3A%22up%20%3D%3D%200%22%2C%22tab%22%3A0%7D%5D',
        'endsAt': '2016-04-21T20:15:37.698Z',
        'startsAt': '2016-04-21T20:14:37.698Z',
        'status': 'firing'
    }
}

_PARAM2 = {
    'externalURL': 'https://am.promehteus.localhost',
    'alert': {
        'labels': {
            'severity': 'critical',
            'alertname': 'service_level_alert',
            'service': 'Service 2'
        },
        'annotations': {
            'service': 'http://example.com/service/{service.id}/'
        },
        'generatorURL': 'https://monitoring.promehteus.localhost/graph#%5B%7B%22expr%22%3A%22up%20%3D%3D%200%22%2C%22tab%22%3A0%7D%5D',
        'endsAt': '2016-04-21T20:15:37.698Z',
        'startsAt': '2016-04-21T20:14:37.698Z',
        'status': 'resolved'
    }
}


class WebhookTest(TestCase):
    @mock.patch('django.db.models.signals.post_save', mock.Mock())
    def setUp(self):
        self.shard = models.Shard.objects.create(name='Shard 1')
        self.service = models.Service.objects.create(name='Service 1', shard=self.shard)
        self.service2 = models.Service.objects.create(name='Service 2', shard=self.shard)

        self.project = models.Project.objects.create(name='Project 1', service=self.service)

        self.sender = models.Sender.create(
            obj=self.project,
            sender=NotificationWebhook.__module__,
            value='http://project.example.com',
        )

        self.sender = models.Sender.create(
            obj=self.service2,
            sender=NotificationWebhook.__module__,
            value='http://service.example.com',
        )

    @override_settings(PROMGEN=TEST_SETTINGS)
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @mock.patch('promgen.util.post')
    def test_webhook(self, mock_post):
        self.client.post(reverse('alert'),
            data=json.dumps(TEST_ALERT),
            content_type='application/json'
        )
        _PARAM1['alert']['annotations']['service'] = _PARAM1['alert']['annotations']['service'].format(service=self.service)
        _PARAM1['alert']['annotations']['project'] = _PARAM1['alert']['annotations']['project'].format(project=self.project)
        _PARAM2['alert']['annotations']['service'] = _PARAM1['alert']['annotations']['service'].format(service=self.service)
        mock_post.assert_has_calls([
            mock.call(
                'http://project.example.com',
                _PARAM1
            ),
            mock.call(
                'http://service.example.com',
                _PARAM2
            )
        ], any_order=True)
