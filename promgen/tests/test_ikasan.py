import mock
from django.test import TestCase, override_settings

from promgen import models
from promgen.sender.ikasan import send
from promgen.tests import TEST_ALERT, TEST_SETTINGS


class IkasanTest(TestCase):
    @mock.patch('django.db.models.signals.post_save', mock.Mock())
    def setUp(self):
        self.service = models.Service.objects.create(name='Service 1')
        self.project = models.Project.objects.create(name='Project 1', service=self.service)
        self.sender = models.Sender.objects.create(
            project=self.project,
            sender='promgen.sender.ikasan',
            value='#',
        )

    @override_settings(PROMGEN=TEST_SETTINGS)
    @mock.patch('requests.post')
    def test_project(self, mock_post):
        send(TEST_ALERT)
        self.assertTrue(mock_post.called)
