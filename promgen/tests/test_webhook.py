from unittest import mock

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase, override_settings

from promgen import models
from promgen.sender.webhook import SenderWebhook
from promgen.tests import TEST_ALERT, TEST_SETTINGS

_PARAMS = {
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


class WebhookTest(TestCase):
    @mock.patch('django.db.models.signals.post_save', mock.Mock())
    def setUp(self):
        self.service = models.Service.objects.create(name='Service 1')
        self.project = models.Project.objects.create(name='Project 1', service=self.service)
        self.project_type = ContentType.objects.get_for_model(self.project)
        self.sender = models.Sender.objects.create(
            object_id=self.project.id,
            content_type_id=self.project_type.id,
            sender='promgen.sender.webhook',
            value='http://example.com',
        )

    @override_settings(PROMGEN=TEST_SETTINGS)
    @mock.patch('requests.post')
    def test_project(self, mock_post):
        self.assertEqual(SenderWebhook().send(TEST_ALERT), 1)
        mock_post.assert_has_calls([
            mock.call(
                'http://example.com',
                _PARAMS
            ),
        ])
