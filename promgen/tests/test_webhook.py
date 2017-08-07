# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import json
from unittest import mock

from django.test import TestCase, override_settings
from django.urls import reverse

from promgen import models
from promgen.notification.webhook import NotificationWebhook
from promgen.tests import TEST_ALERT, TEST_SETTINGS


class WebhookTest(TestCase):
    @mock.patch('django.db.models.signals.post_save', mock.Mock())
    def setUp(self):
        self.shard = models.Shard.objects.create(name='Shard 1')
        self.service = models.Service.objects.create(name='Service 1', shard=self.shard)
        self.project = models.Project.objects.create(name='Project 1', service=self.service)

        self.sender = models.Sender.create(
            obj=self.project,
            sender=NotificationWebhook.__module__,
            value='http://project.example.com',
        )

        self.sender = models.Sender.create(
            obj=self.service,
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

        # Our sample is the same as the original, with some annotations added
        _SAMPLE = TEST_ALERT.copy()
        _SAMPLE['commonAnnotations']['service'] = 'http://example.com' + self.service.get_absolute_url()
        _SAMPLE['commonAnnotations']['project'] = 'http://example.com' + self.project.get_absolute_url()
        mock_post.assert_has_calls([
            mock.call(
                'http://project.example.com',
                _SAMPLE
            ),
            mock.call(
                'http://service.example.com',
                _SAMPLE
            )
        ], any_order=True)
