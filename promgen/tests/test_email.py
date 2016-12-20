from unittest import mock
from django.test import TestCase, override_settings

from promgen import models
from promgen.sender.email import send
from promgen.tests import TEST_ALERT, TEST_SETTINGS


_SUBJECT = 'node_down foo-BETA testhost.localhost:9100 node resolved'
_MESSAGE = '''node_down foo-BETA testhost.localhost:9100 node resolved

description: testhost.localhost:9100 of job node has been down for more than 5 minutes.
summary: Instance testhost.localhost:9100 down

Prometheus: https://monitoring.promehteus.localhost/graph#%5B%7B%22expr%22%3A%22up%20%3D%3D%200%22%2C%22tab%22%3A0%7D%5D
Alert Manager: https://am.promehteus.localhost'''


class LineNotifyTest(TestCase):
    @mock.patch('django.db.models.signals.post_save', mock.Mock())
    def setUp(self):
        self.service = models.Service.objects.create(name='Service 1')
        self.project = models.Project.objects.create(name='Project 1', service=self.service)
        self.project2 = models.Project.objects.create(name='Project 2', service=self.service)
        self.sender = models.Sender.objects.create(
            project=self.project,
            sender='promgen.sender.email',
            value='example@example.com',
        )
        models.Sender.objects.create(
            project=self.project,
            sender='promgen.sender.email',
            value='foo@example.com',
        )
        models.Sender.objects.create(
            project=self.project2,
            sender='promgen.sender.email',
            value='bar@example.com',
        )

    @override_settings(PROMGEN=TEST_SETTINGS)
    @mock.patch('promgen.sender.email.send_mail')
    def test_project(self, mock_email):
        self.assertTrue(send(TEST_ALERT))
        mock_email.assert_has_calls([
            mock.call(
                _SUBJECT,
                _MESSAGE,
                'promgen@example.com',
                ['example@example.com']
            ),
            mock.call(
                _SUBJECT,
                _MESSAGE,
                'promgen@example.com',
                ['foo@example.com']
            )
        ])
        # Three senders are registered but only two should trigger
        self.assertTrue(mock_email.call_count == 2)
