# Copyright (c) 2018 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE
import json
from unittest import mock

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
                    if isinstance(obj, models.Group):
                        obj.user_set.add(user)

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
                        if isinstance(obj, models.Group):
                            obj.user_set.remove(user)
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
    def test_rest_farm(self):
        remote_driver = mock.Mock(remote=True)
        local_driver = mock.Mock(remote=False)
        with (
            mock.patch.object(
                models.Farm,
                "driver_set",
                return_value=[("promgen", local_driver), ("mock-remote", remote_driver)],
            ),
            mock.patch.object(
                models.Farm,
                "fetch",
                return_value=["mock-farm-a", "mock-farm-b"],
            ),
            mock.patch.object(models.Farm, "refresh", return_value=(set(), set())),
        ):
            cases = tests.Data("cases", "test_rest_farm.csv").csv()
            for case in cases:
                self._run_rest_test(case)

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

    @override_settings(PROMGEN=tests.SETTINGS)
    def test_rest_rule(self):
        cases = tests.Data("cases", "test_rest_rule.csv").csv()
        for case in cases:
            self._run_rest_test(case)

    @override_settings(PROMGEN=tests.SETTINGS)
    def test_rest_exporter(self):
        cases = tests.Data("cases", "test_rest_exporter.csv").csv()
        for case in cases:
            self._run_rest_test(case)

    @override_settings(PROMGEN=tests.SETTINGS)
    def test_rest_url(self):
        cases = tests.Data("cases", "test_rest_url.csv").csv()
        for case in cases:
            self._run_rest_test(case)

    @override_settings(PROMGEN=tests.SETTINGS)
    def test_rest_group(self):
        # Initialize test data
        admin = User.objects.get(username="admin")
        test_group = models.Group.objects.get(pk=1)
        test_group.user_set.add(admin)
        assign_perm("group_admin", admin, test_group)
        test_service = models.Service.objects.get(pk=1)
        assign_perm("service_admin", test_group, test_service)

        cases = tests.Data("cases", "test_rest_group.csv").csv()
        for case in cases:
            self._run_rest_test(case)

            # Delete newly created group to avoid affecting other tests
            if case["case"] == "An authenticated user without permissions can create a group.":
                models.Group.objects.get(name="new-group").delete()

    @override_settings(PROMGEN=tests.SETTINGS)
    def test_rest_project(self):
        remote_driver = mock.Mock(remote=True)
        local_driver = mock.Mock(remote=False)
        with (
            mock.patch.object(
                models.Farm,
                "driver_set",
                return_value=[("promgen", local_driver), ("mock-remote", remote_driver)],
            ),
            mock.patch.object(
                models.Farm,
                "fetch",
                return_value=["mock-farm-a", "mock-farm-b"],
            ),
        ):
            cases = tests.Data("cases", "test_rest_project.csv").csv()
            for case in cases:
                # Delete the current farm to test linking new farm
                if case["case"] == "An editor can link farm to a project.":
                    project = models.Project.objects.get(id=1)
                    project.farm.delete()
                    project.refresh_from_db()

                self._run_rest_test(case)

    @override_settings(PROMGEN=tests.SETTINGS)
    def test_rest_project__changing_owner(self):
        # Prepare test data
        admin = User.objects.get(username="admin")
        admin_token = Token.objects.filter(user=admin).first().key
        user = User.objects.get(username="demo")
        user_token = Token.objects.filter(user=user).first().key
        project = models.Project.objects.get(id=1)
        assign_perm("project_admin", user, project)

        response = self.client.patch(
            reverse("api-v2:project-detail", kwargs={"id": 1}),
            data={"owner": "demo"},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Token {admin_token}",
        )
        self.assertEqual(response.status_code, 200, "Site Admin can change project owner.")

        response = self.client.patch(
            reverse("api-v2:project-detail", kwargs={"id": 1}),
            data={"owner": "admin"},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Token {user_token}",
        )
        self.assertEqual(response.status_code, 200, "Current owner can change project owner.")

        response = self.client.patch(
            reverse("api-v2:project-detail", kwargs={"id": 1}),
            data={"owner": "demo"},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Token {user_token}",
        )
        self.assertEqual(
            response.status_code, 400, "Non-owner project admin cannot change project owner."
        )
        self.assertEqual(
            response.json(), {"owner": "You do not have permission to change the owner."}
        )

    @override_settings(PROMGEN=tests.SETTINGS)
    def test_rest_project__deleting_project(self):
        # Prepare test data
        admin = User.objects.get(username="admin")
        admin_token = Token.objects.filter(user=admin).first().key
        user = User.objects.get(username="demo")
        user_token = Token.objects.filter(user=user).first().key

        response = self.client.delete(
            reverse("api-v2:project-detail", kwargs={"id": 1}),
            HTTP_AUTHORIZATION=f"Token {admin_token}",
        )
        self.assertEqual(response.status_code, 204, "Site Admin can delete project.")

        # Recreate the deleted project for the next test case
        models.Project.objects.create(name="test-project", owner_id=1, shard_id=1, service_id=1)
        project = models.Project.objects.get(name="test-project")
        assign_perm("project_admin", user, project)

        response = self.client.delete(
            reverse("api-v2:project-detail", kwargs={"id": project.pk}),
            HTTP_AUTHORIZATION=f"Token {user_token}",
        )
        self.assertEqual(
            response.status_code, 403, "Non-owner project admin cannot delete project."
        )

        project.owner = user
        project.save()
        project.refresh_from_db()

        response = self.client.delete(
            reverse("api-v2:project-detail", kwargs={"id": project.pk}),
            HTTP_AUTHORIZATION=f"Token {user_token}",
        )
        self.assertEqual(response.status_code, 204, "Project owner can delete project.")

        # Recreate the deleted project for the next test case
        models.Project.objects.create(name="test-project", owner_id=1, shard_id=1, service_id=1)
        project = models.Project.objects.get(name="test-project")
        assign_perm("service_admin", user, project.service)

        response = self.client.delete(
            reverse("api-v2:project-detail", kwargs={"id": project.pk}),
            HTTP_AUTHORIZATION=f"Token {user_token}",
        )
        self.assertEqual(
            response.status_code, 403, "Non-owner service admin cannot delete project."
        )

        service = project.service
        service.owner = user
        service.save()
        service.refresh_from_db()

        response = self.client.delete(
            reverse("api-v2:project-detail", kwargs={"id": project.pk}),
            HTTP_AUTHORIZATION=f"Token {user_token}",
        )
        self.assertEqual(response.status_code, 204, "Service owner can delete project.")
