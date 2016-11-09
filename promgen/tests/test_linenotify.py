from unittest import mock
from django.test import TestCase, override_settings

from promgen import models
from promgen.sender.linenotify import send
from promgen.tests import TEST_ALERT, TEST_SETTINGS


_MESSAGE = '''node_down foo-BETA testhost.localhost:9100 node resolved

Instance testhost.localhost:9100 down
testhost.localhost:9100 of job node has been down for more than 5 minutes.

Prometheus: https://monitoring.promehteus.localhost/graph#%5B%7B%22expr%22%3A%22up%20%3D%3D%200%22%2C%22tab%22%3A0%7D%5D
Alert Manager: https://am.promehteus.localhost'''


class LineNotifyTest(TestCase):
    @mock.patch('django.db.models.signals.post_save', mock.Mock())
    def setUp(self):
        self.service = models.Service.objects.create(name='Service 1')
        self.project = models.Project.objects.create(name='Project 1', service=self.service)
        self.sender = models.Sender.objects.create(
            project=self.project,
            sender='promgen.sender.linenotify',
            value='hogehoge',
        )

    @override_settings(PROMGEN=TEST_SETTINGS)
    @mock.patch('requests.post')
    def test_project(self, mock_post):
        self.assertTrue(send(TEST_ALERT))
        mock_post.assert_called_once_with(
            'https://notify.example',
            data={'message': _MESSAGE},
            headers={'Authorization': 'Bearer hogehoge'},
        )
