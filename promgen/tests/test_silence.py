# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import datetime
from unittest import mock

from django.test import override_settings
from django.urls import reverse

from promgen import tests

TEST_SETTINGS = tests.Data('examples', 'promgen.yml').yaml()
TEST_DURATION = tests.Data('examples', 'silence.duration.json').json()
TEST_RANGE = tests.Data('examples', 'silence.range.json').json()

# Explicitly set a timezone for our test to try to catch conversion errors
TEST_SETTINGS['timezone'] = 'Asia/Tokyo'


class SilenceTest(tests.PromgenTest):
    @mock.patch("django.dispatch.dispatcher.Signal.send")
    def setUp(self, mock_signal):
        self.user = self.add_force_login(id=999, username="Foo")

    @override_settings(PROMGEN=TEST_SETTINGS)
    @mock.patch('promgen.util.post')
    def test_duration(self, mock_post):
        mock_post.return_value.status_code = 200

        with mock.patch('django.utils.timezone.now') as mock_now:
            mock_now.return_value = datetime.datetime(2017, 12, 14, tzinfo=datetime.timezone.utc)
            # I would prefer to be able to test with multiple labels, but since
            # it's difficult to test a list of dictionaries (the order is non-
            # deterministic) we just test with a single label for now
            self.client.post(
                reverse('proxy-silence'),
                data={
                    'duration': '1m',
                    "labels": {"instance": "example.com:[0-9]*"},
                },
                content_type="application/json",
            )
        mock_post.assert_called_with(
            'http://alertmanager:9093/api/v1/silences',
            json=TEST_DURATION
        )

    @override_settings(PROMGEN=TEST_SETTINGS)
    @mock.patch('promgen.util.post')
    def test_range(self, mock_post):
        mock_post.return_value.status_code = 200

        with mock.patch('django.utils.timezone.now') as mock_now:
            mock_now.return_value = datetime.datetime(2017, 12, 14, tzinfo=datetime.timezone.utc)
            self.client.post(
                reverse('proxy-silence'),
                data={
                    'startsAt': '2017-12-14 00:01',
                    'endsAt': '2017-12-14 00:05',
                    "labels": {"instance": "example.com:[0-9]*"},
                },
                content_type="application/json",
            )
        mock_post.assert_called_with(
            'http://alertmanager:9093/api/v1/silences',
            json=TEST_RANGE
        )
