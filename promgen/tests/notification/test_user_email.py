# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

from unittest import mock

from django.contrib.auth.models import Permission
from django.test import override_settings

from promgen import models, rest, tests
from promgen.notification.email import NotificationEmail
from promgen.notification.linenotify import NotificationLineNotify
from promgen.notification.user import NotificationUser


class UserSplayTest(tests.PromgenTest):
    def setUp(self):
        self.user = self.force_login(username="demo")
        permission = Permission.objects.get(codename="process_alert")
        self.user.user_permissions.add(permission)

    @override_settings(PROMGEN=tests.SETTINGS)
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @mock.patch("promgen.notification.email.send_mail")
    @mock.patch("promgen.util.post")
    def test_user_splay(self, mock_email, mock_post):
        one = models.Service.objects.get(pk=1)

        NotificationUser.create(obj=one, value=str(one.owner.pk), owner=self.user)
        NotificationLineNotify.create(obj=one.owner, value="#foo", owner=self.user)
        NotificationEmail.create(obj=one.owner, value="foo@bar.example", owner=self.user)

        response = self.fireAlert()
        self.assertRoute(response, rest.AlertReceiver, 202)
        self.assertCount(models.Alert, 1, "Alert Queued")
        self.assertCount(models.AlertError, 0, "No failed alerts")

        # Since we test the specifics elsewhere, just want to check
        # the count of calls here
        self.assertEqual(mock_post.call_count, 1, "Called LINE Notify")
        self.assertEqual(mock_email.call_count, 1, "Called email")

    @override_settings(PROMGEN=tests.SETTINGS)
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @mock.patch("promgen.notification.email.send_mail")
    def test_failed_user(self, mock_email):
        # We have one valid sender and one invalid one
        # The invalid one should be skipped while still letting
        # the valid one pass
        one = models.Service.objects.get(pk=1)
        NotificationEmail.create(obj=one, value="foo@bar.example", owner=self.user)
        NotificationUser.create(obj=one, value="0", owner=self.user)

        response = self.fireAlert()
        self.assertRoute(response, rest.AlertReceiver, 202)
        self.assertCount(models.Alert, 1, "Alert Queued")
        self.assertCount(models.AlertError, 0, "No failed alerts")

        self.assertEqual(mock_email.call_count, 1, "Still called email")

    @override_settings(PROMGEN=tests.SETTINGS)
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @mock.patch("promgen.notification.email.send_mail")
    def test_enabled(self, mock_email):
        one = models.Service.objects.get(pk=1)

        # This notification is direct and disabled
        NotificationEmail.create(
            obj=one, value="disabled.example@example.com", enabled=False, owner=self.user
        )
        # Our parent notification is enabled
        NotificationUser.create(obj=one, value=str(one.owner.pk), owner=self.user)
        # But the child notifier is disabled and shouldn't fire
        NotificationEmail.create(
            obj=one.owner, value="enabled.example@example.com", enabled=False, owner=self.user
        )

        response = self.fireAlert()
        self.assertRoute(response, rest.AlertReceiver, 202)
        self.assertCount(models.Alert, 1, "Alert Queued")
        self.assertCount(models.AlertError, 0, "No failed alerts")

        self.assertEqual(mock_email.call_count, 0, "Should not call email")
