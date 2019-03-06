# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from promgen import models
from promgen.notification.email import NotificationEmail
from promgen.notification.ikasan import NotificationIkasan
from promgen.notification.user import NotificationUser
from promgen.tests import PromgenTest

TEST_SETTINGS = PromgenTest.data_yaml('examples', 'promgen.yml')
TEST_ALERT = PromgenTest.data('examples', 'alertmanager.json')


class UserEmailTest(TestCase):
    @mock.patch('django.dispatch.dispatcher.Signal.send')
    def setUp(self, mock_signal):
        self.user = User.objects.create_user(id=999, username="Foo")
        self.shard = models.Shard.objects.create(name='test.shard')
        self.service = models.Service.objects.create(name='test.service', shard=self.shard)

        self.sender = models.Sender.objects.create(
            obj=self.service,
            sender=NotificationUser.__module__,
            value=self.user.username,
        )

        models.Sender.objects.create(
            obj=self.user,
            sender=NotificationIkasan.__module__,
            value='#foo'
        )

        models.Sender.objects.create(
            obj=self.user,
            sender=NotificationEmail.__module__,
            value='foo@bar.example'
        )

    @override_settings(PROMGEN=TEST_SETTINGS)
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @mock.patch('promgen.notification.email.send_mail')
    @mock.patch('promgen.util.post')
    def test_user_notification(self, mock_email, mock_post):
        self.client.post(reverse('alert'),
            data=TEST_ALERT,
            content_type='application/json'
        )

        # Since we test the specifics elsewhere, just want to check
        # the count of calls here
        self.assertEqual(mock_post.call_count, 1, 'Called Email')
        self.assertEqual(mock_email.call_count, 1, 'Called Ikasan')
