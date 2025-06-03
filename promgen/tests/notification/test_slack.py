# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

from unittest import mock

from django.contrib.auth.models import Permission
from django.test import override_settings

from promgen import models, rest, tests
from promgen.notification.slack import NotificationSlack


class SlackTest(tests.PromgenTest):
    TestHook1 = "https://hooks.slack.com/services/XXXXXXXXX/XXXXXXXXX/XXXXXXXXXXXXXXXXXXXXXXXX"
    TestHook2 = "https://hooks.slack.com/services/YYYYYYYYY/YYYYYYYYY/YYYYYYYYYYYYYYYYYYYYYYYY"

    def setUp(self):
        one = models.Project.objects.get(pk=1)
        two = models.Service.objects.get(pk=2)
        self.user = self.force_login(username="demo")

        NotificationSlack.create(obj=one, value=self.TestHook1, owner=self.user)
        NotificationSlack.create(obj=two, value=self.TestHook2, owner=self.user)

        self.user = self.force_login(username="demo")
        permission = Permission.objects.get(codename="process_alert")
        self.user.user_permissions.add(permission)

    @override_settings(PROMGEN=tests.SETTINGS)
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @mock.patch("promgen.util.post")
    def test_slack(self, mock_post):
        response = self.fireAlert()
        self.assertRoute(response, rest.AlertReceiver, 202)
        self.assertCount(models.AlertError, 0)

        # Swap the status to test our resolved alert
        SAMPLE = tests.Data("examples", "alertmanager.json").json()
        SAMPLE["status"] = "resolved"
        SAMPLE["commonLabels"]["service"] = "other-service"
        SAMPLE["commonLabels"].pop("project")
        response = self.fireAlert(data=SAMPLE)
        self.assertRoute(response, rest.AlertReceiver, 202)
        self.assertCount(models.AlertError, 0)

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
