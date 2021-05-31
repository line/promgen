# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

from unittest import mock

from django.test import override_settings

from promgen import models, rest, tests
from promgen.notification.email import NotificationEmail


class EmailTest(tests.PromgenTest):
    fixtures = ["testcases.yaml"]

    @mock.patch("django.dispatch.dispatcher.Signal.send")
    def setUp(self, mock_signal):
        one = models.Project.objects.get(pk=1)
        two = models.Project.objects.get(pk=2)

        NotificationEmail.create(obj=one, value="example@example.com")
        NotificationEmail.create(obj=one, value="foo@example.com")
        NotificationEmail.create(obj=two, value="bar@example.com")

    @override_settings(PROMGEN=tests.SETTINGS)
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @mock.patch("promgen.notification.email.send_mail")
    def test_email(self, mock_email):
        response = self.fireAlert()
        self.assertRoute(response, rest.AlertReceiver, 202)
        self.assertCount(models.AlertError, 0, "No failed alerts")

        _SUBJECT = tests.Data("notification", "email.subject.txt").raw().strip()
        _MESSAGE = tests.Data("notification", "email.body.txt").raw().strip()

        mock_email.assert_has_calls(
            [
                mock.call(
                    _SUBJECT, _MESSAGE, "promgen@example.com", ["example@example.com"]
                ),
                mock.call(
                    _SUBJECT, _MESSAGE, "promgen@example.com", ["foo@example.com"]
                ),
            ],
            any_order=True,
        )
        # Three senders are registered but only two should trigger
        self.assertTrue(mock_email.call_count == 2)
