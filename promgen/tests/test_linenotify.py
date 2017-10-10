# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import json
from unittest import mock

from django.test import override_settings
from django.urls import reverse

from promgen import models
from promgen.notification.linenotify import NotificationLineNotify
from promgen.tests import PromgenTest

TEST_SETTINGS = PromgenTest.data_yaml('examples', 'promgen.yml')
TEST_ALERT = PromgenTest.data('examples', 'alertmanager.json')


class LineNotifyTest(PromgenTest):
    @mock.patch('django.dispatch.dispatcher.Signal.send')
    def setUp(self, mock_signal):
        self.shard = models.Shard.objects.create(name='test.shard')
        self.service = models.Service.objects.create(name='test.service', shard=self.shard)
        self.project = models.Project.objects.create(name='test.project', service=self.service)
        self.sender = models.Sender.create(
            obj=self.project,
            sender=NotificationLineNotify.__module__,
            value='hogehoge',
        )

        self.service2 = models.Service.objects.create(name='other.service', shard=self.shard)
        self.sender2 = models.Sender.create(
            obj=self.service2,
            sender=NotificationLineNotify.__module__,
            value='asdfasdf',
        )

    @override_settings(PROMGEN=TEST_SETTINGS)
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @mock.patch('promgen.util.post')
    def test_line_notify(self, mock_post):
        self.client.post(reverse('alert'),
            data=TEST_ALERT,
            content_type='application/json'
        )

        # Swap the status to test our resolved alert
        SAMPLE = PromgenTest.data_json('examples', 'alertmanager.json')
        SAMPLE['status'] = 'resolved'
        SAMPLE['commonLabels']['service'] = self.service2.name
        SAMPLE['commonLabels'].pop('project')
        self.client.post(reverse('alert'),
            data=json.dumps(SAMPLE),
            content_type='application/json'
        )

        _MESSAGE = PromgenTest.data('notifications', 'linenotify.body.txt').strip()
        _RESOLVED = PromgenTest.data('notifications', 'linenotify.resolved.txt').strip()

        mock_post.assert_has_calls([
            mock.call(
                'https://notify.example',
                data={'message': _MESSAGE.format(service=self.service, project=self.project)},
                headers={'Authorization': 'Bearer hogehoge'},
            ),
            mock.call(
                'https://notify.example',
                data={'message': _RESOLVED},
                headers={'Authorization': 'Bearer asdfasdf'},
            ),
        ], any_order=True)
