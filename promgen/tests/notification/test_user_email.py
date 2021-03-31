# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

from unittest import mock

from django.test import override_settings

from promgen import models, tests
from promgen.notification.email import NotificationEmail
from promgen.notification.linenotify import NotificationLineNotify
from promgen.notification.user import NotificationUser


class UserEmailTest(tests.PromgenTest):
    fixtures = ["testcases.yaml"]

    @mock.patch("django.dispatch.dispatcher.Signal.send")
    def setUp(self, mock_signal):
        one = models.Service.objects.get(pk=1)

        models.Sender.objects.create(
            obj=one,
            sender=NotificationUser.__module__,
            value=one.owner,
        )

        models.Sender.objects.create(
            obj=one.owner, sender=NotificationLineNotify.__module__, value="#foo"
        )

        models.Sender.objects.create(
            obj=one.owner, sender=NotificationEmail.__module__, value="foo@bar.example"
        )

    @override_settings(PROMGEN=tests.SETTINGS)
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @mock.patch("promgen.notification.email.send_mail")
    @mock.patch("promgen.util.post")
    def test_user_notification(self, mock_email, mock_post):
        self.testAlert()

        # Since we test the specifics elsewhere, just want to check
        # the count of calls here
        self.assertEqual(mock_post.call_count, 1, "Called LINE Notify")
        self.assertEqual(mock_email.call_count, 1, "Called email")
