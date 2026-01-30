# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import datetime
from unittest import mock

from django.test import override_settings
from django.urls import reverse

from promgen import errors, forms, tests

TEST_SETTINGS = tests.Data("examples", "promgen.yml").yaml()
TEST_DURATION = tests.Data("examples", "silence.duration.json").json()
TEST_RANGE = tests.Data("examples", "silence.range.json").json()

# Explicitly set a timezone for our test to try to catch conversion errors
TEST_SETTINGS["timezone"] = "Asia/Tokyo"


class SilenceTest(tests.PromgenTest):
    fixtures = ["testcases.yaml", "extras.yaml"]

    def setUp(self):
        self.user = self.force_login(username="admin")

    @override_settings(PROMGEN=TEST_SETTINGS)
    @mock.patch("promgen.util.post")
    def test_duration(self, mock_post):
        mock_post.return_value.status_code = 200

        with mock.patch("django.utils.timezone.now") as mock_now:
            mock_now.return_value = datetime.datetime(2017, 12, 14, tzinfo=datetime.timezone.utc)
            # I would prefer to be able to test with multiple labels, but since
            # it's difficult to test a list of dictionaries (the order is non-
            # deterministic) we just test with a single label for now
            self.client.post(
                reverse("proxy-silence"),
                data={
                    "duration": "1m",
                    "labels": {"instance": "example.com:[0-9]*"},
                },
                content_type="application/json",
            )
        mock_post.assert_called_with("http://alertmanager:9093/api/v2/silences", json=TEST_DURATION)

    @override_settings(PROMGEN=TEST_SETTINGS)
    @mock.patch("promgen.util.post")
    def test_range(self, mock_post):
        mock_post.return_value.status_code = 200

        with mock.patch("django.utils.timezone.now") as mock_now:
            mock_now.return_value = datetime.datetime(2017, 12, 14, tzinfo=datetime.timezone.utc)
            self.client.post(
                reverse("proxy-silence"),
                data={
                    "startsAt": "2017-12-14 00:01",
                    "endsAt": "2017-12-14 00:05",
                    "labels": {"instance": "example.com:[0-9]*"},
                },
                content_type="application/json",
            )

        mock_post.assert_called_with("http://alertmanager:9093/api/v2/silences", json=TEST_RANGE)

    @override_settings(PROMGEN=TEST_SETTINGS)
    def test_site_silence_errors(self):
        form = forms.SilenceForm(data={"labels": {}, "duration": "1m"})
        self.assertEqual(
            form.errors.as_data(),
            {"__all__": [errors.SilenceError.NOLABEL.error()]},
        )

        form = forms.SilenceForm(data={"labels": {"alertname": "example-rule"}, "duration": "1m"})
        self.assertEqual(
            form.errors.as_data(),
            {"__all__": [errors.SilenceError.GLOBALSILENCE.error()]},
        )

        form = forms.SilenceForm(
            data={"labels": {"alertname": "example-rule", "foo": "bar"}, "duration": "1m"}
        )
        self.assertEqual(
            form.errors.as_data(),
            {"__all__": [errors.SilenceError.GLOBALSILENCE.error()]},
        )

        form = forms.SilenceForm(
            data={"labels": {"alertname": "example-rule", "service": "foo"}, "duration": "1m"}
        )
        self.assertEqual(form.errors, {}, "Expected no errors")
        self.assertEqual(
            form.cleaned_data,
            {
                "comment": "Silenced from Promgen",
                "createdBy": "Promgen",
                "duration": "1m",
                "endsAt": "",
                "labels": {"alertname": "example-rule", "service": "foo"},
                "startsAt": "",
            },
        )
