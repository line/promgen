# Copyright (c) 2018 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE


from django.contrib.auth.models import Permission
from django.test import override_settings
from django.urls import reverse

from promgen import models, rest, tests


class RestAPITest(tests.PromgenTest):
    def setUp(self):
        self.user = self.force_login(username="demo")

    @override_settings(PROMGEN=tests.SETTINGS)
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_alert_blackhole(self):
        permission = Permission.objects.get(codename="process_alert")
        self.user.user_permissions.add(permission)

        response = self.fireAlert("heartbeat.json")
        self.assertRoute(response, rest.AlertReceiver, 202)
        self.assertCount(models.Alert, 0, "Heartbeat alert should be deleted")

    @override_settings(PROMGEN=tests.SETTINGS)
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_alert(self):
        permission = Permission.objects.get(codename="process_alert")
        self.user.user_permissions.add(permission)

        response = self.fireAlert()
        self.assertEqual(response.status_code, 202)
        self.assertCount(models.Alert, 1, "Alert Queued")

    @override_settings(PROMGEN=tests.SETTINGS)
    def test_retrieve_farm(self):
        expected = tests.Data("examples", "rest.farm.json").json()

        # Check retrieving all farms
        response = self.client.get(reverse("api:farm-list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # Check retrieving all farms whose "name" contains "farm"
        response = self.client.get(reverse("api:farm-list"), {"name": "farm"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # Check retrieving all farms whose "source" is "promgen"
        response = self.client.get(reverse("api:farm-list"), {"source": "promgen"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # Check retrieving farms with a non-existent "name" returns an empty list
        response = self.client.get(reverse("api:farm-list"), {"name": "other-name"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

        # Check retrieving farms with a non-existent "source" returns an empty list
        response = self.client.get(reverse("api:farm-list"), {"source": "other-source"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)


        farm = models.Farm.objects.get(id=1)
        models.Host.objects.create(name="host.example.com", farm=farm)
        expected = tests.Data("examples", "rest.farm.1.json").json()

        # Check retrieving the farm whose "id" is "1", including the list of hosts.
        response = self.client.get(reverse("api:farm-detail", args=[1]))
        self.assertEqual(response.json(), expected)
