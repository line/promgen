# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

from unittest import mock

from django.test import override_settings

from promgen import models, rest, tests
from promgen.notification.webhook import NotificationWebhook


class WebhookTest(tests.PromgenTest):
    fixtures = ["testcases.yaml"]

    @mock.patch("django.dispatch.dispatcher.Signal.send")
    def setUp(self, mock_signal):
        one = models.Project.objects.get(pk=1)
        two = models.Service.objects.get(pk=1)

        self.senderA = NotificationWebhook.create(
            obj=one, value="http://webhook.example.com/project"
        )
        self.senderB = NotificationWebhook.create(
            obj=two, value="http://webhook.example.com/service"
        )

    @override_settings(PROMGEN=tests.SETTINGS)
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @override_settings(CELERY_TASK_EAGER_PROPAGATES=True)
    @mock.patch("promgen.util.post")
    def test_webhook(self, mock_post):
        response = self.fireAlert()

        self.assertRoute(response, rest.AlertReceiver, 202)
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

        self.assertCount(models.Alert, 1, "Alert should be queued")
        self.assertEqual(mock_post.call_count, 1, "One notification should be skipped")

    @override_settings(PROMGEN=tests.SETTINGS)
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @override_settings(CELERY_TASK_EAGER_PROPAGATES=True)
    @mock.patch("promgen.util.post")
    def test_failure(self, mock_post):
        # When our post results in a failure, then our error_count should be
        # properly updated and some errors should be logged to be viewed later
        mock_post.side_effect = Exception("Boom!")

        response = self.fireAlert()

        self.assertRoute(response, rest.AlertReceiver, 202)
        self.assertCount(models.Alert, 1, "Alert should be queued")
        self.assertEqual(mock_post.call_count, 2, "Two posts should be attempted")
        self.assertCount(models.AlertError, 2, "Two errors should be logged")

        alert = models.Alert.objects.first()
        self.assertEqual(alert.sent_count, 0, "No successful sent")
        self.assertEqual(alert.error_count, 2, "Error incremented")
