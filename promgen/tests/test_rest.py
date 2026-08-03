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

from promgen import models, plugins, rest, signals, tests
from promgen.notification.email import NotificationEmail


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
    def test_retrieve_farm(self):
        self.user = self.force_login(username="demo")
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

        # Check retrieving farms with a non-existent "source" returns 400 Bad Request
        response = self.client.get(reverse("api:farm-list"), {"source": "other-source"})
        self.assertEqual(response.status_code, 400)

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

    @override_settings(PROMGEN=tests.SETTINGS)
    def test_rest_notifier_alias(self):
        self.user = self.force_login(username="admin")
        service = models.Service.objects.get(pk=1)
        notifier = NotificationEmail.create(
            obj=service, value="true_email@example.com", owner=self.user
        )

        response = self.client.get(reverse("api-v2:sender-list"), {"value": "true_email"})
        self.assertEqual(response.data["count"], 1, "Expected one notifier matching the filter")
        self.assertEqual(
            response.data["results"][0]["value"],
            "true_email@example.com",
            "Expected the notifier's value to match the real email",
        )

        notifier.alias = "alias"
        notifier.save()

        response = self.client.get(reverse("api-v2:sender-list"), {"value": "true_email"})
        self.assertEqual(
            response.data["count"],
            0,
            "Expected no notifiers matching the filter after alias is set",
        )

        response = self.client.get(reverse("api-v2:sender-list"), {"value": "alias"})
        self.assertEqual(
            response.data["count"],
            1,
            "Expected one notifier matching the filter after alias is set",
        )
        self.assertIsNone(
            response.data["results"][0]["value"],
            "Expected the notifier's value to be null",
        )
        self.assertEqual(
            response.data["results"][0]["alias"],
            "alias",
            "Expected the notifier's alias to match the alias",
        )

    @override_settings(PROMGEN=tests.SETTINGS)
    def test_rest_rule(self):
        cases = tests.Data("cases", "test_rest_rule.csv").csv()
        for case in cases:
            self._run_rest_test(case)

    def test_rest_farm(self):
        local_driver = mock.Mock(remote=False)
        local_driver.name = "promgen"
        local_driver.load.return_value = mock.Mock(return_value=mock.Mock(remote=False))
        remote_driver = mock.Mock(remote=True)
        remote_driver.name = "external"
        remote_driver.load.return_value = mock.Mock(return_value=mock.Mock(remote=True))
        with (
            mock.patch.object(plugins, "discovery", return_value=[local_driver, remote_driver]),
            mock.patch.object(
                models.Farm,
                "driver_set",
                return_value=[
                    (local_driver.name, local_driver),
                    (remote_driver.name, remote_driver),
                ],
            ),
            mock.patch.object(models.Farm, "fetch", return_value=["other-farm", "other-farm-2"]),
            mock.patch.object(models.Farm, "refresh", return_value=(set(), set())),
        ):
            cases = tests.Data("cases", "test_rest_farm.csv").csv()
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
        cases = tests.Data("cases", "test_rest_project.csv").csv()
        for case in cases:
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
            data={"owner": 2},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Token {admin_token}",
        )
        self.assertEqual(response.status_code, 200, "Site Admin can change project owner.")

        response = self.client.patch(
            reverse("api-v2:project-detail", kwargs={"id": 1}),
            data={"owner": 1},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Token {user_token}",
        )
        self.assertEqual(response.status_code, 200, "Current owner can change project owner.")

        response = self.client.patch(
            reverse("api-v2:project-detail", kwargs={"id": 1}),
            data={"owner": 2},
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

    @override_settings(PROMGEN=tests.SETTINGS)
    def test_rest_project__registering_farm(self):
        # Prepare test data
        user = User.objects.get(username="demo")
        user_token = Token.objects.filter(user=user).first().key
        project = models.Project.objects.get(id=1)
        assign_perm("project_editor", user, project)

        # 1. User cannot register a farm if project already has a farm.
        response = self.client.post(
            reverse("api-v2:project-farms", kwargs={"id": 1}),
            data={"name": "test-farm", "source": "promgen", "hosts": ["test-host-1"]},
            HTTP_AUTHORIZATION=f"Token {user_token}",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"detail": "Project already has a farm."})

        # Delete the farm for next case
        farm = project.farm
        farm.delete()

        # 2. User can register a local farm to project
        response = self.client.post(
            reverse("api-v2:project-farms", kwargs={"id": 1}),
            data={"name": "test-farm", "source": "promgen", "hosts": ["test-host-1"]},
            HTTP_AUTHORIZATION=f"Token {user_token}",
        )
        self.assertEqual(response.status_code, 201, "User can register a local farm to project.")

        # Delete the farm for next case
        project.refresh_from_db()
        farm = project.farm
        farm.delete()

        # 3. User can link a remote farm to project
        remote_driver = mock.Mock(remote=True)
        remote_driver.name = "external"
        remote_driver.load.return_value = mock.Mock(return_value=mock.Mock(remote=True))
        with (
            mock.patch.object(plugins, "discovery", return_value=[remote_driver]),
            mock.patch.object(
                models.Farm, "driver_set", return_value=[(remote_driver.name, remote_driver)]
            ),
            mock.patch.object(models.Farm, "fetch", return_value=["other-farm"]),
            mock.patch.object(models.Farm, "refresh", return_value=(set(), set())),
        ):
            # 3.1. Farm source must be existing driver.
            response = self.client.post(
                reverse("api-v2:project-farms", kwargs={"id": 1}),
                data={"name": "other-farm", "source": "other-external"},
                HTTP_AUTHORIZATION=f"Token {user_token}",
            )
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json(), {"source": "Unknown farm source."})

            # 3.2. Farm must be existing in the driver.
            response = self.client.post(
                reverse("api-v2:project-farms", kwargs={"id": 1}),
                data={"name": "farm", "source": "external"},
                HTTP_AUTHORIZATION=f"Token {user_token}",
            )
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json(), {"farm": "Unknown farm."})

            # 3.3. User can link a remote farm to project.
            response = self.client.post(
                reverse("api-v2:project-farms", kwargs={"id": 1}),
                data={"name": "other-farm", "source": "external"},
                HTTP_AUTHORIZATION=f"Token {user_token}",
            )
            self.assertEqual(response.status_code, 201, "User can link a remote farm to project.")

    @override_settings(PROMGEN=tests.SETTINGS)
    def test_rest_service(self):
        cases = tests.Data("cases", "test_rest_service.csv").csv()
        for case in cases:
            self._run_rest_test(case)

            # Delete newly created service to avoid affecting other tests
            if case["case"] == "An authenticated user without permissions can create a service.":
                models.Service.objects.get(name="new-service").delete()

    @override_settings(PROMGEN=tests.SETTINGS)
    def test_rest_service__changing_owner(self):
        # Prepare test data
        admin = User.objects.get(username="admin")
        admin_token = Token.objects.filter(user=admin).first().key
        user = User.objects.get(username="demo")
        user_token = Token.objects.filter(user=user).first().key
        service = models.Service.objects.get(id=1)
        assign_perm("service_admin", user, service)

        response = self.client.patch(
            reverse("api-v2:service-detail", kwargs={"id": 1}),
            data={"owner": 2},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Token {admin_token}",
        )
        self.assertEqual(response.status_code, 200, "Site Admin can change service owner.")

        response = self.client.patch(
            reverse("api-v2:service-detail", kwargs={"id": 1}),
            data={"owner": 1},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Token {user_token}",
        )
        self.assertEqual(response.status_code, 200, "Current owner can change service owner.")

        response = self.client.patch(
            reverse("api-v2:service-detail", kwargs={"id": 1}),
            data={"owner": 2},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Token {user_token}",
        )
        self.assertEqual(
            response.status_code, 400, "Non-owner service admin cannot change service owner."
        )
        self.assertEqual(
            response.json(), {"owner": "You do not have permission to change the owner."}
        )

    @override_settings(PROMGEN=tests.SETTINGS)
    def test_rest_service__deleting_service(self):
        # Prepare test data
        admin = User.objects.get(username="admin")
        admin_token = Token.objects.filter(user=admin).first().key
        user = User.objects.get(username="demo")
        user_token = Token.objects.filter(user=user).first().key

        response = self.client.delete(
            reverse("api-v2:service-detail", kwargs={"id": 1}),
            HTTP_AUTHORIZATION=f"Token {admin_token}",
        )
        self.assertEqual(response.status_code, 204, "Site Admin can delete service.")

        # Recreate the deleted service for the next test case
        models.Service.objects.create(name="test-service", owner_id=1)
        service = models.Service.objects.get(name="test-service")
        assign_perm("service_admin", user, service)

        response = self.client.delete(
            reverse("api-v2:service-detail", kwargs={"id": service.pk}),
            HTTP_AUTHORIZATION=f"Token {user_token}",
        )
        self.assertEqual(
            response.status_code, 403, "Non-owner service admin cannot delete service."
        )

        service.owner = user
        service.save()
        service.refresh_from_db()

        response = self.client.delete(
            reverse("api-v2:service-detail", kwargs={"id": service.pk}),
            HTTP_AUTHORIZATION=f"Token {user_token}",
        )
        self.assertEqual(response.status_code, 204, "Service owner can delete service.")
