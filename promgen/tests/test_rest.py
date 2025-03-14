# Copyright (c) 2018 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE


from django.contrib.auth.models import Permission
from django.test import override_settings
from django.urls import reverse
from rest_framework.authtoken.models import Token

from promgen import models, rest, tests


class RestAPITest(tests.PromgenTest):
    def setUp(self):
        super().setUp()

    @override_settings(PROMGEN=tests.SETTINGS)
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_alert_blackhole(self):
        self.user = self.force_login(username="demo")
        permission = Permission.objects.get(codename="process_alert")
        self.user.user_permissions.add(permission)

        response = self.fireAlert("heartbeat.json")
        self.assertRoute(response, rest.AlertReceiver, 202)
        self.assertCount(models.Alert, 0, "Heartbeat alert should be deleted")

    @override_settings(PROMGEN=tests.SETTINGS)
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_alert(self):
        self.user = self.force_login(username="demo")
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

    @override_settings(PROMGEN=tests.SETTINGS)
    def test_rest_user(self):
        token = Token.objects.filter(user__username="demo").first().key

        # Check retrieving all users without token returns 401 Unauthorized
        response = self.client.get(reverse("api-v2:user-list"))
        self.assertEqual(response.status_code, 401)

        # Check retrieving all users
        expected = tests.Data("examples", "rest.user.default.json").json()
        response = self.client.get(reverse("api-v2:user-list"), HTTP_AUTHORIZATION=f"Token {token}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # Check retrieving paginated users
        expected = tests.Data("examples", "rest.user.paginated.json").json()
        response = self.client.get(
            reverse("api-v2:user-list"),
            {"page_number": 1, "page_size": 1},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # Check retrieving users whose "username" contains "demo"
        expected = tests.Data("examples", "rest.user.filter_by_username.json").json()
        response = self.client.get(
            reverse("api-v2:user-list"), {"username": "demo"}, HTTP_AUTHORIZATION=f"Token {token}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # Check retrieving users with a non-existent "username" returns an empty list
        response = self.client.get(
            reverse("api-v2:user-list"),
            {"username": "non-existent"},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)

        # Check retrieving users whose "email" contains "demo@example"
        expected = tests.Data("examples", "rest.user.filter_by_email.json").json()
        response = self.client.get(
            reverse("api-v2:user-list"),
            {"email": "demo@example"},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # Check retrieving users with a non-existent "email" returns an empty list
        response = self.client.get(
            reverse("api-v2:user-list"),
            {"email": "non-existent"},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)

        # Check retrieving the current user without token returns 401 Unauthorized
        response = self.client.get(reverse("api-v2:user-get-current-user"))
        self.assertEqual(response.status_code, 401)

        # Check retrieving the current user with token returns the expected user
        expected = tests.Data("examples", "rest.user.get_current_user.json").json()
        response = self.client.get(
            reverse("api-v2:user-get-current-user"), HTTP_AUTHORIZATION=f"Token {token}"
        )
        response_json = response.json()
        # date_joined is not a fixed value when running tests, so we need to skip it
        response_json["date_joined"] = None
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_json, expected)
