# Copyright (c) 2018 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE


from django.test import override_settings

from promgen import models, tests, views


class RestAPITest(tests.PromgenTest):
    @override_settings(PROMGEN=tests.SETTINGS)
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_alert_blackhole(self):
        response = self.testAlert("heartbeat.json")
        self.assertRoute(response, views.Alert, 202)
        self.assertCount(models.Alert, 0, "Heartbeat alert should be deleted")

    @override_settings(PROMGEN=tests.SETTINGS)
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_alert(self):
        response = self.testAlert()
        self.assertEqual(response.status_code, 202)
