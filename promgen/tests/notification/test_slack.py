# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

from unittest import mock

from django.test import override_settings

from promgen import models, tests
from promgen.notification.slack import NotificationSlack


class SlackTest(tests.PromgenTest):
    fixtures = ["testcases.yaml"]

    TestHook1 = (
        "https://hooks.slack.com/services/XXXXXXXXX/XXXXXXXXX/XXXXXXXXXXXXXXXXXXXXXXXX"
    )
    TestHook2 = (
        "https://hooks.slack.com/services/YYYYYYYYY/YYYYYYYYY/YYYYYYYYYYYYYYYYYYYYYYYY"
    )

    @mock.patch("django.dispatch.dispatcher.Signal.send")
    def setUp(self, mock_signal):
        one = models.Project.objects.get(pk=1)
        two = models.Service.objects.get(pk=2)

        models.Sender.objects.create(
            obj=one,
            sender=NotificationSlack.__module__,
            value=self.TestHook1,
        )

        models.Sender.objects.create(
            obj=two,
            sender=NotificationSlack.__module__,
            value=self.TestHook2,
        )

    @override_settings(PROMGEN=tests.SETTINGS)
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @mock.patch("promgen.util.post")
    def test_slack(self, mock_post):
        self.fireAlert()

        # Swap the status to test our resolved alert
        SAMPLE = tests.Data("examples", "alertmanager.json").json()
        SAMPLE["status"] = "resolved"
        SAMPLE["commonLabels"]["service"] = "other-service"
        SAMPLE["commonLabels"].pop("project")
        self.fireAlert(data=SAMPLE)

        _MESSAGE = tests.Data("notification", "slack.body.txt").raw().strip()
        _RESOLVED = tests.Data("notification", "slack.resolved.txt").raw().strip()

        mock_post.assert_has_calls(
            [
                mock.call(
                    self.TestHook1,
                    json={"text": _MESSAGE},
                ),
                mock.call(
                    self.TestHook2,
                    json={"text": _RESOLVED},
                ),
            ],
            any_order=True,
        )
