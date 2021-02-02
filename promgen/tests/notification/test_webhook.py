# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

from unittest import mock

from django.test import override_settings
from django.urls import reverse

from promgen import models, tests, views
from promgen.notification.webhook import NotificationWebhook

TEST_SETTINGS = tests.Data("examples", "promgen.yml").yaml()
TEST_ALERT = tests.Data("examples", "alertmanager.json").raw()


class WebhookTest(tests.PromgenTest):
    @mock.patch("django.dispatch.dispatcher.Signal.send")
    def setUp(self, mock_signal):
        self.shard = models.Shard.objects.create(name="test.shard")
        self.service = models.Service.objects.create(name="test.service")
        self.project = models.Project.objects.create(
            name="test.project", service=self.service, shard=self.shard
        )

        self.senderA = models.Sender.objects.create(
            obj=self.project,
            sender=NotificationWebhook.__module__,
            value="http://project.example.com",
        )

        self.senderB = models.Sender.objects.create(
            obj=self.service,
            sender=NotificationWebhook.__module__,
            value="http://service.example.com",
        )

    @override_settings(PROMGEN=TEST_SETTINGS)
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @override_settings(CELERY_TASK_EAGER_PROPAGATES=True)
    @mock.patch("promgen.util.post")
    def test_webhook(self, mock_post):
        response = self.client.post(
            reverse("alert"), data=TEST_ALERT, content_type="application/json"
        )

        self.assertRoute(response, views.Alert, 202)
        self.assertCount(models.Alert, 1, "Alert should be queued")
        self.assertEqual(mock_post.call_count, 2, "Two alerts should be sent")

        # Our sample is the same as the original, with some annotations added
        _SAMPLE = tests.Data("examples", "alertmanager.json").json()
        _SAMPLE["externalURL"] = "http://example.com/alert/11"
        _SAMPLE["commonAnnotations"]["service"] = (
            "http://example.com" + self.service.get_absolute_url()
        )
        _SAMPLE["commonAnnotations"]["project"] = (
            "http://example.com" + self.project.get_absolute_url()
        )

        mock_post.assert_has_calls(
            [
                mock.call("http://project.example.com", json=_SAMPLE),
                mock.call("http://service.example.com", json=_SAMPLE),
            ],
            any_order=True,
        )

    @override_settings(PROMGEN=TEST_SETTINGS)
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @override_settings(CELERY_TASK_EAGER_PROPAGATES=True)
    @mock.patch("promgen.util.post")
    def test_filter(self, mock_post):
        # Our first sender will only allow critical messages
        models.Filter.objects.create(
            sender=self.senderA, name="severity", value="critical"
        )

        # Our second sender allows critical and major
        models.Filter.objects.create(
            sender=self.senderB, name="severity", value="critical"
        )
        models.Filter.objects.create(
            sender=self.senderB, name="severity", value="major"
        )

        self.assertCount(models.Filter, 3, "Should be three filters")

        response = self.client.post(
            reverse("alert"), data=TEST_ALERT, content_type="application/json"
        )
        self.assertRoute(response, views.Alert, 202)

        self.assertCount(models.Alert, 1, "Alert should be queued")
        self.assertEqual(mock_post.call_count, 1, "One notification should be skipped")

    @override_settings(PROMGEN=TEST_SETTINGS)
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @override_settings(CELERY_TASK_EAGER_PROPAGATES=True)
    @mock.patch("promgen.util.post")
    def test_failure(self, mock_post):
        # When our post results in a failure, then our error_count should be
        # properly updated and some errors should be logged to be viewed later
        mock_post.side_effect = Exception("Boom!")

        response = self.client.post(
            reverse("alert"), data=TEST_ALERT, content_type="application/json"
        )

        self.assertRoute(response, views.Alert, 202)
        self.assertCount(models.Alert, 1, "Alert should be queued")
        self.assertEqual(mock_post.call_count, 2, "Two posts should be attempted")
        self.assertCount(models.AlertError, 2, "Two errors should be logged")

        alert = models.Alert.objects.first()
        self.assertEqual(alert.sent_count, 0, "No successful sent")
        self.assertEqual(alert.error_count, 2, "Error incremented")
