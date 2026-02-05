# Copyright (c) 2026 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

from unittest import mock

from django.contrib.auth.models import Permission
from django.test import override_settings

from promgen import models, rest, tests
from promgen.notification.alertmanager import NotificationAlertmanager


class AlertmanagerTest(tests.PromgenTest):
    def setUp(self):
        one = models.Project.objects.get(pk=1)
        two = models.Service.objects.get(pk=1)

        self.senderA = NotificationAlertmanager.create(
            obj=one, value="http://alertmanager/api/v2/alerts", owner_id=1
        )
        self.senderB = NotificationAlertmanager.create(
            obj=two, value="http://alertmanager_2/api/v2/alerts", owner_id=1
        )

        self.user = self.force_login(username="demo")
        permission = Permission.objects.get(codename="process_alert")
        self.user.user_permissions.add(permission)

    @override_settings(PROMGEN=tests.SETTINGS)
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @override_settings(CELERY_TASK_EAGER_PROPAGATES=True)
    @mock.patch("promgen.util.post")
    def test_alertmanager(self, mock_post):
        response = self.fireAlert()
        self.assertRoute(response, rest.AlertReceiver, 202)
        self.assertCount(models.AlertError, 0, "No failed alerts")

        self.assertCount(models.Alert, 1, "Alert should be queued")
        self.assertEqual(mock_post.call_count, 2, "Two alerts should be sent")

        # Our sample is the same as the original's "alerts" field.
        _SAMPLE = tests.Data("notification", "alertmanager.json").json()

        mock_post.assert_has_calls(
            [
                mock.call("http://alertmanager/api/v2/alerts", json=_SAMPLE),
                mock.call("http://alertmanager_2/api/v2/alerts", json=_SAMPLE),
            ],
            any_order=True,
        )
