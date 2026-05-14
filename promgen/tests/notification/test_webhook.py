# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

from unittest import mock

from django.contrib.auth.models import Permission
from django.test import override_settings
from requests.exceptions import RequestException

from promgen import models, rest, tests
from promgen.notification.webhook import NotificationWebhook


class WebhookTest(tests.PromgenTest):
    def setUp(self):
        one = models.Project.objects.get(pk=1)
        two = models.Service.objects.get(pk=1)

        # Firstly, clear all Sender data in test database to ensure avoiding data conflicts
        # without having to make too many changes in old tests.
        models.Sender.objects.all().delete()

        self.senderA = NotificationWebhook.create(
            obj=one, value="http://webhook.example.com/project", owner_id=1
        )
        self.senderB = NotificationWebhook.create(
            obj=two, value="http://webhook.example.com/service", owner_id=1
        )

        self.user = self.force_login(username="demo")
        permission = Permission.objects.get(codename="process_alert")
        self.user.user_permissions.add(permission)

    @override_settings(PROMGEN=tests.SETTINGS)
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @override_settings(CELERY_TASK_EAGER_PROPAGATES=True)
    @mock.patch("promgen.util.post")
    def test_webhook(self, mock_post):
        response = self.fireAlert()
        self.assertRoute(response, rest.AlertReceiver, 202)
        self.assertCount(models.AlertError, 0, "No failed alerts")

        self.assertCount(models.Alert, 1, "Alert should be queued")
        self.assertEqual(mock_post.call_count, 2, "Two alerts should be sent")

        # Our sample is the same as the original, with some annotations added
        _SAMPLE = tests.Data("notification", "webhook.json").json()
        # External URL is depended on test order
        _SAMPLE["externalURL"] = mock.ANY

        mock_post.assert_has_calls(
            [
                mock.call("http://webhook.example.com/project", json=_SAMPLE),
                mock.call("http://webhook.example.com/service", json=_SAMPLE),
            ],
            any_order=True,
        )

    @override_settings(PROMGEN=tests.SETTINGS)
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @override_settings(CELERY_TASK_EAGER_PROPAGATES=True)
    @mock.patch("promgen.util.post")
    def test_filter(self, mock_post):
        # Our first sender will only allow critical messages
        self.senderA.filter_set.create(name="severity", value="critical")

        # Our second sender allows critical and major
        self.senderB.filter_set.create(name="severity", value="critical")
        self.senderB.filter_set.create(name="severity", value="major")

        self.assertCount(models.Filter, 3, "Should be three filters")

        response = self.fireAlert()
        self.assertRoute(response, rest.AlertReceiver, 202)
        self.assertCount(models.AlertError, 0, "No failed alerts")
        self.assertCount(models.Alert, 1, "Alert should be queued")
        self.assertEqual(mock_post.call_count, 1, "One notification should be skipped")

    @override_settings(PROMGEN=tests.SETTINGS)
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @override_settings(CELERY_TASK_EAGER_PROPAGATES=True)
    @mock.patch("promgen.util.post")
    def test_failure(self, mock_post):
        # When our post results in a failure, then our error_count should be
        # properly updated and some errors should be logged to be viewed later
        mock_post.side_effect = RequestException("Boom!")

        response = self.fireAlert()
        self.assertRoute(response, rest.AlertReceiver, 202)
        self.assertCount(models.Alert, 1, "Alert should be queued")
        self.assertCount(models.AlertError, 2, "Two errors should be logged")
        self.assertEqual(mock_post.call_count, 2, "Two posts should be attempted")

        alert = models.Alert.objects.first()
        self.assertEqual(alert.sent_count, 0, "No successful sent")
        self.assertEqual(alert.error_count, 2, "Error incremented")
