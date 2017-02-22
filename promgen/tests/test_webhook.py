import json
from unittest import mock

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase, override_settings
from django.urls import reverse
from promgen import models
from promgen.sender.webhook import SenderWebhook
from promgen.tests import TEST_ALERT, TEST_SETTINGS

_PARAM1 = {
    'alertmanager': 'https://am.promehteus.localhost',
    'alertname': 'node_down',
    'description': 'testhost.localhost:9100 of job node has been down for more than 5 minutes.',
    'env': 'prod',
    'farm': 'foo-BETA',
    'instance': 'testhost.localhost:9100',
    'job': 'node',
    'project': 'Project 1',
    'prometheus': 'https://monitoring.promehteus.localhost/graph#%5B%7B%22expr%22%3A%22up%20%3D%3D%200%22%2C%22tab%22%3A0%7D%5D',
    'service': 'Service 1',
    'severity': 'critical',
    'status': 'resolved',
    'summary': 'Instance testhost.localhost:9100 down',
}

_PARAM2 = {
    'alertmanager': 'https://am.promehteus.localhost',
    'alertname': 'service_level_alert',
    'prometheus': 'https://monitoring.promehteus.localhost/graph#%5B%7B%22expr%22%3A%22up%20%3D%3D%200%22%2C%22tab%22%3A0%7D%5D',
    'service': 'Service 2',
    'severity': 'critical',
    'status': 'firing',
}


class WebhookTest(TestCase):
    @mock.patch('django.db.models.signals.post_save', mock.Mock())
    def setUp(self):
        self.shard = models.Shard.objects.create(name='Shard 1')
        self.service = models.Service.objects.create(name='Service 1', shard=self.shard)
        self.service2 = models.Service.objects.create(name='Service 2', shard=self.shard)

        self.project = models.Project.objects.create(name='Project 1', service=self.service)

        self.project_type = ContentType.objects.get_for_model(self.project)
        self.service_type = ContentType.objects.get_for_model(self.service)

        self.sender = models.Sender.objects.create(
            object_id=self.project.id,
            content_type_id=self.project_type.id,
            sender=SenderWebhook.__module__,
            value='http://project.example.com',
        )

        self.sender = models.Sender.objects.create(
            object_id=self.service2.id,
            content_type_id=self.service_type.id,
            sender=SenderWebhook.__module__,
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
