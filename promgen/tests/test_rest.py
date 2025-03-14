# Copyright (c) 2018 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE
import json

from django.apps import apps as django_apps
from django.contrib.auth.models import Permission, User
from django.db.models.signals import post_delete, post_save
from django.test import override_settings
from django.urls import reverse
from guardian.models import UserObjectPermission
from guardian.shortcuts import assign_perm, remove_perm
from rest_framework.authtoken.models import Token

from promgen import models, rest, signals, tests


class RestAPITest(tests.PromgenTest):
    def _run_rest_test(self, case):
        def _parse_case_json(value, default):
            if not value:
                return default
            return json.loads(value)

        with self.subTest(case=case["case"]):
            user = case["user"]
            token = None
            permissions = _parse_case_json(case.get("permissions"), [])
            viewname = case["viewname"]
            method = case["method"].lower()
            kwargs = _parse_case_json(case.get("kwargs"), {})
            payload = _parse_case_json(case.get("payload"), None)
            expected_status = int(case["expected_status"])
            expected_response = _parse_case_json(case.get("expected_response"), {})

            if user:
                user = User.objects.get(username=case["user"])
                token = Token.objects.filter(user=user).first().key
                for permission in permissions:
                    perm = permission["codename"]
                    app_label, model_name = permission["model"].split(".")
                    obj_pk = permission["obj_pk"]
                    model = django_apps.get_model(app_label, model_name)
                    obj = model.objects.get(pk=obj_pk)
                    assign_perm(perm, user, obj)

            url = reverse(viewname, kwargs=kwargs or None)
            request_kwargs = {}
            if payload is not None:
                request_kwargs["data"] = payload
                request_kwargs["content_type"] = "application/json"
            if user:
                request_kwargs["HTTP_AUTHORIZATION"] = f"Token {token}"

            response = getattr(self.client, method)(url, **request_kwargs)

            self.assertEqual(
                response.status_code,
                expected_status,
                f"expected status {expected_status} but got {response.status_code}",
            )

            if "count" in expected_response:
                self.assertEqual(
                    response.data["count"],
                    expected_response["count"],
                    "count mismatch",
                )
            if "results_length" in expected_response:
                self.assertEqual(
                    len(response.data["results"]),
                    expected_response["results_length"],
                    "results length mismatch",
                )
            if "example" in expected_response:
                self.assertEqual(
                    response.json(),
                    tests.Data("examples", expected_response["example"]).json(),
                    "response body mismatch",
                )
            if "response_body" in expected_response:
                self.assertEqual(
                    response.json(),
                    expected_response["response_body"],
                    "response body mismatch",
                )

            # Clean up permissions after the test case
            if user:
                for permission in permissions:
                    perm = permission["codename"]
                    app_label, model_name = permission["model"].split(".")
                    obj_pk = permission["obj_pk"]
                    model = django_apps.get_model(app_label, model_name)
                    try:
                        obj = model.objects.get(pk=obj_pk)
                        remove_perm(perm, user, obj)
                    except model.DoesNotExist:
                        pass

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

        # Check retrieving all farms without assigning permissions return empty list
        response = self.client.get(reverse("api:farm-list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

        # Check retrieving a specific farm without assigning permissions return 404 Not Found
        response = self.client.get(reverse("api:farm-detail", args=[1]))
        self.assertEqual(response.status_code, 404)

        # Assigning permissions to the user
        assign_perm("project_viewer", self.user, models.Project.objects.get(id=1))

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
    def test_rest_audit(self):
        post_save.disconnect(signals.create_log, sender=UserObjectPermission)
        post_delete.disconnect(signals.delete_log, sender=UserObjectPermission)

        cases = tests.Data("cases", "test_rest_audit.csv").csv()
        for case in cases:
            self._run_rest_test(case)

    @override_settings(PROMGEN=tests.SETTINGS)
    def test_rest_notifier(self):
        cases = tests.Data("cases", "test_rest_notifier.csv").csv()
        for case in cases:
            self._run_rest_test(case)
