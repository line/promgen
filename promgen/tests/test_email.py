import json
from unittest import mock

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase, override_settings
from django.urls import reverse

from promgen import models
from promgen.notification.email import NotificationEmail
from promgen.tests import TEST_ALERT, TEST_SETTINGS

_SUBJECT = '[resolved] node_down foo-BETA testhost.localhost:9100 node'
_MESSAGE = '''node_down foo-BETA testhost.localhost:9100 node resolved

description: testhost.localhost:9100 of job node has been down for more than 5 minutes.
summary: Instance testhost.localhost:9100 down

Prometheus: https://monitoring.promehteus.localhost/graph#%5B%7B%22expr%22%3A%22up%20%3D%3D%200%22%2C%22tab%22%3A0%7D%5D
Alert Manager: https://am.promehteus.localhost'''


class EmailTest(TestCase):
    @mock.patch('django.db.models.signals.post_save', mock.Mock())
    def setUp(self):
        self.shard = models.Shard.objects.create(name='Shard 1')
        self.service = models.Service.objects.create(name='Service 1', shard=self.shard)
        self.project = models.Project.objects.create(name='Project 1', service=self.service)
        self.project2 = models.Project.objects.create(name='Project 2', service=self.service)
        project_type = ContentType.objects.get_for_model(self.project)
        self.sender = models.Sender.objects.create(
            object_id=self.project.id,
            content_type_id=project_type.id,
            sender=NotificationEmail.__module__,
            value='example@example.com',
        )
        models.Sender.objects.create(
            object_id=self.project.id,
            content_type_id=project_type.id,
            sender=NotificationEmail.__module__,
            value='foo@example.com',
        )
        models.Sender.objects.create(
            object_id=self.project2.id,
            content_type_id=project_type.id,
            sender=NotificationEmail.__module__,
            value='bar@example.com',
        )

    @override_settings(PROMGEN=TEST_SETTINGS)
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @mock.patch('promgen.notification.email.send_mail')
    def test_email(self, mock_email):
        self.client.post(reverse('alert'),
            data=json.dumps(TEST_ALERT),
            content_type='application/json'
        )
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
