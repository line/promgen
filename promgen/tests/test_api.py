# Copyright (c) 2018 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE


from django.test import override_settings
from django.urls import reverse

from promgen import models, views
from promgen.tests import PromgenTest

TEST_SETTINGS = PromgenTest.data_yaml('examples', 'promgen.yml')

TEST_HEARTBEAT = PromgenTest.data('examples', 'heartbeat.json')


class APITest(PromgenTest):
    @override_settings(PROMGEN=TEST_SETTINGS)
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_alert_blackhole(self):
        response = self.client.post(
            reverse('alert'), data=TEST_HEARTBEAT, content_type='application/json'
        )
        self.assertRoute(response, views.Alert, 202)
        self.assertCount(models.Alert, 0, "Heartbeat alert should be deleted")
