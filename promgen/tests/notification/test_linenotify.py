# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

from unittest import mock

from django.test import override_settings

from promgen import models, tests, rest
from promgen.notification.linenotify import NotificationLineNotify


class LineNotifyTest(tests.PromgenTest):
    fixtures = ["testcases.yaml"]

    @mock.patch("django.dispatch.dispatcher.Signal.send")
    def setUp(self, mock_signal):
        one = models.Project.objects.get(pk=1)
        two = models.Service.objects.get(pk=2)

        NotificationLineNotify.create(obj=one, value="hogehoge")
        NotificationLineNotify.create(obj=two, value="asdfasdf")

    @override_settings(PROMGEN=tests.SETTINGS)
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @mock.patch("promgen.util.post")
    def test_line_notify(self, mock_post):
        response = self.fireAlert()
        self.assertRoute(response, rest.AlertReceiver, 202)

        # Swap the status to test our resolved alert
        SAMPLE = tests.Data("examples", "alertmanager.json").json()
        SAMPLE["status"] = "resolved"
        SAMPLE["commonLabels"]["service"] = "other-service"
        SAMPLE["commonLabels"].pop("project")
        response = self.fireAlert(data=SAMPLE)
        self.assertRoute(response, rest.AlertReceiver, 202)

        _MESSAGE = tests.Data("notification", "linenotify.body.txt").raw().strip()
        _RESOLVED = tests.Data("notification", "linenotify.resolved.txt").raw().strip()

        mock_post.assert_has_calls(
            [
                mock.call(
                    "https://notify.example",
                    data={"message": _MESSAGE},
                    headers={"Authorization": "Bearer hogehoge"},
                ),
                mock.call(
                    "https://notify.example",
                    data={"message": _RESOLVED},
                    headers={"Authorization": "Bearer asdfasdf"},
                ),
            ],
            any_order=True,
        )
