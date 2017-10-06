# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

from unittest import mock

from django.test import override_settings
from django.urls import reverse

from promgen import models
from promgen.notification.webhook import NotificationWebhook
from promgen.tests import PromgenTest


TEST_SETTINGS = PromgenTest.data_yaml('examples', 'promgen.yml')
TEST_ALERT = PromgenTest.data('examples', 'alertmanager.json')


class WebhookTest(PromgenTest):
    @mock.patch('django.db.models.signals.post_save', mock.Mock())
    def setUp(self):
        self.shard = models.Shard.objects.create(name='test.shard')
        self.service = models.Service.objects.create(name='test.service', shard=self.shard)
        self.project = models.Project.objects.create(name='test.project', service=self.service)

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
            data=TEST_ALERT,
            content_type='application/json'
        )

        # Our sample is the same as the original, with some annotations added
        _SAMPLE = PromgenTest.data_json('examples', 'alertmanager.json')
        _SAMPLE['commonAnnotations']['service'] = 'http://example.com' + self.service.get_absolute_url()
        _SAMPLE['commonAnnotations']['project'] = 'http://example.com' + self.project.get_absolute_url()

        from pprint import pprint
        pprint(TEST_ALERT)
        pprint(_SAMPLE)

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
