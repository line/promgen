# Copyright (c) 2018 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE


from django.contrib.auth.models import Permission, User
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

    @override_settings(PROMGEN=tests.SETTINGS)
    def test_rest_audit(self):
        token = Token.objects.filter(user__username="demo").first().key

        # Check retrieving all audits without token returns 401 Unauthorized
        response = self.client.get(reverse("api-v2:audit-list"))
        self.assertEqual(response.status_code, 401)

        # Check retrieving all audits
        expected = tests.Data("examples", "rest.audit.default.json").json()
        response = self.client.get(
            reverse("api-v2:audit-list"),
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # Check retrieving paginated audits
        expected = tests.Data("examples", "rest.audit.paginated.json").json()
        response = self.client.get(
            reverse("api-v2:audit-list"),
            {"page_number": 1, "page_size": 1},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # Check retrieving audits whose "content_type" is "service"
        expected = tests.Data("examples", "rest.audit.filter_by_content_type.json").json()
        response = self.client.get(
            reverse("api-v2:audit-list"),
            {"content_type": "service"},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # Check retrieving audits with a non-allowed "content_type" returns 400 Bad Request
        response = self.client.get(
            reverse("api-v2:audit-list"),
            {"content_type": "non-allowed"},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 400)

        # Check retrieving audits whose "object_id" is "1"
        expected = tests.Data("examples", "rest.audit.filter_by_object_id.json").json()
        response = self.client.get(
            reverse("api-v2:audit-list"),
            {"object_id": "1"},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # Check retrieving audits with a non-existent "object_id" returns an empty list
        response = self.client.get(
            reverse("api-v2:audit-list"),
            {"object_id": "-1"},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)

        # Check retrieving audits whose "user" is "demo"
        expected = tests.Data("examples", "rest.audit.filter_by_user.json").json()
        response = self.client.get(
            reverse("api-v2:audit-list"),
            {"user": "demo"},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # Check retrieving audits with a non-existent "user" returns an empty list
        response = self.client.get(
            reverse("api-v2:audit-list"),
            {"user": "non-existent"},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)

    @override_settings(PROMGEN=tests.SETTINGS)
    def test_rest_notifier(self):
        token = Token.objects.filter(user__username="demo").first().key

        # Check retrieving notifiers without token returns 401 Unauthorized
        response = self.client.get(reverse("api-v2:sender-list"))
        self.assertEqual(response.status_code, 401)

        # Check retrieving all notifiers
        expected = tests.Data("examples", "rest.notifier.default.json").json()
        response = self.client.get(
            reverse("api-v2:sender-list"),
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # Check retrieving paginated notifiers
        expected = tests.Data("examples", "rest.notifier.paginated.json").json()
        response = self.client.get(
            reverse("api-v2:sender-list"),
            {"page_number": 1, "page_size": 1},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # Check retrieving notifiers whose "content_type" is "service"
        expected = tests.Data("examples", "rest.notifier.filter_by_content_type.json").json()
        response = self.client.get(
            reverse("api-v2:sender-list"),
            {"content_type": "service"},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # Check retrieving notifiers with a non-allowed "content_type" returns 400 Bad Request
        response = self.client.get(
            reverse("api-v2:sender-list"),
            {"content_type": "non-allowed"},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 400)

        # Check retrieving notifiers whose "object_id" is "1"
        expected = tests.Data("examples", "rest.notifier.filter_by_object_id.json").json()
        response = self.client.get(
            reverse("api-v2:sender-list"),
            {"object_id": "1"},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # Check retrieving notifiers with a non-existent "object_id" returns an empty list
        response = self.client.get(
            reverse("api-v2:sender-list"),
            {"object_id": "-1"},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)

        # Check retrieving notifiers whose "owner" is "demo"
        expected = tests.Data("examples", "rest.notifier.filter_by_owner.json").json()
        response = self.client.get(
            reverse("api-v2:sender-list"),
            {"owner": "demo"},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # Check retrieving notifiers with a non-existent "owner" returns an empty list
        response = self.client.get(
            reverse("api-v2:sender-list"),
            {"owner": "non-existent"},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)

        # Check retrieving notifiers whose "sender" is "promgen.notification.email"
        expected = tests.Data("examples", "rest.notifier.filter_by_sender.json").json()
        response = self.client.get(
            reverse("api-v2:sender-list"),
            {"sender": "promgen.notification.email"},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # Check retrieving notifiers with a non-existent "sender" returns 400 Bad Request
        response = self.client.get(
            reverse("api-v2:sender-list"),
            {"sender": "non-existent"},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 400)

        # Check retrieving notifiers whose "value" contains "general"
        expected = tests.Data("examples", "rest.notifier.filter_by_value.json").json()
        response = self.client.get(
            reverse("api-v2:sender-list"),
            {"value": "services"},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # Check retrieving notifiers with a non-existent "value" returns an empty list
        response = self.client.get(
            reverse("api-v2:sender-list"),
            {"value": "non-existent"},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)

        # Check update a notifier without token returns 401 Unauthorized
        response = self.client.put(
            reverse("api-v2:sender-detail", args=[1]),
            {"enabled": False},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

        # Check update a notifier without permission returns 403 Forbidden
        response = self.client.put(
            reverse("api-v2:sender-detail", args=[1]),
            {"enabled": False},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 403)

        # Check partial update a notifier without token returns 401 Unauthorized
        response = self.client.patch(
            reverse("api-v2:sender-detail", args=[1]),
            {"enabled": False},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

        # Check partial update a notifier without permission returns 403 Forbidden
        response = self.client.patch(
            reverse("api-v2:sender-detail", args=[1]),
            {"enabled": False},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 403)

        # Check add filter for a notifier without token returns 401 Unauthorized
        response = self.client.post(
            reverse("api-v2:sender-add-filter", args=[1]),
            {"name": "name", "value": "value"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

        # Check add filter for a notifier without permission returns 403 Forbidden
        response = self.client.post(
            reverse("api-v2:sender-add-filter", args=[1]),
            {"name": "name", "value": "value"},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 403)

        # Check delete filter for a notifier without token returns 401 Unauthorized
        response = self.client.delete(
            reverse("api-v2:sender-delete-filter", args=[1, 1]),
        )
        self.assertEqual(response.status_code, 401)

        # Check delete filter for a notifier without permission returns 403 Forbidden
        response = self.client.delete(
            reverse("api-v2:sender-delete-filter", args=[1, 1]),
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 403)

        # Check delete a notifier without token returns 401 Unauthorized
        response = self.client.delete(
            reverse("api-v2:sender-detail", args=[1]),
        )
        self.assertEqual(response.status_code, 401)

        # Check delete a notifier without permission returns 403 Forbidden
        response = self.client.delete(
            reverse("api-v2:sender-detail", args=[1]), HTTP_AUTHORIZATION=f"Token {token}"
        )
        self.assertEqual(response.status_code, 403)

        user = User.objects.get(username="demo")
        user.user_permissions.add(Permission.objects.get(codename="add_sender"))
        user.user_permissions.add(Permission.objects.get(codename="change_sender"))
        user.user_permissions.add(Permission.objects.get(codename="delete_sender"))

        # Check update a notifier successfully with permission
        notifier = models.Sender.objects.get(id=1)
        notifier.enabled = True
        response = self.client.put(
            reverse("api-v2:sender-detail", args=[1]),
            {"enabled": False},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        notifier.refresh_from_db()
        self.assertFalse(notifier.enabled)

        # Check partial update a notifier successfully with permission
        notifier = models.Sender.objects.get(id=1)
        notifier.enabled = True
        response = self.client.patch(
            reverse("api-v2:sender-detail", args=[1]),
            {"enabled": False},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        notifier.refresh_from_db()
        self.assertFalse(notifier.enabled)

        # Check add filter for a notifier successfully with permission
        response = self.client.post(
            reverse("api-v2:sender-add-filter", args=[2]),
            {"name": "name", "value": "value"},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 201)
        # skip comparing the ID
        # and make sure the rest of the input from the request is the same as the output
        for item in response.data["filters"]:
            item.pop("id", None)
        self.assertEqual(response.data["filters"], [{"name": "name", "value": "value"}])

        # Check delete filter for a notifier successfully with permission
        response = self.client.delete(
            reverse("api-v2:sender-delete-filter", args=[2, 2]),
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 204)

        # Check delete a notifier successfully with permission
        response = self.client.delete(
            reverse("api-v2:sender-detail", args=[1]), HTTP_AUTHORIZATION=f"Token {token}"
        )
        self.assertEqual(response.status_code, 204)

    @override_settings(PROMGEN=tests.SETTINGS)
    def test_rest_rule(self):
        token = Token.objects.filter(user__username="demo").first().key

        # Check retrieving all rules
        expected = tests.Data("examples", "rest.rule.default.json").json()
        response = self.client.get(
            reverse("api-v2:rule-list"),
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # Check retrieving paginated rules
        expected = tests.Data("examples", "rest.rule.paginated.json").json()
        response = self.client.get(
            reverse("api-v2:rule-list"),
            {"page_number": 1, "page_size": 1},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # Check retrieving rules whose "content_type" is "service"
        expected = tests.Data("examples", "rest.rule.filter_by_content_type.json").json()
        response = self.client.get(
            reverse("api-v2:rule-list"),
            {"content_type": "service"},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # Check retrieving rules with a non-allowed "content_type" returns 400 Bad Request
        response = self.client.get(
            reverse("api-v2:rule-list"),
            {"content_type": "non-allowed"},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 400)

        # Check retrieving rules whose "object_id" is "1"
        expected = tests.Data("examples", "rest.rule.filter_by_object_id.json").json()
        response = self.client.get(
            reverse("api-v2:rule-list"),
            {"object_id": "1"},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # Check retrieving rules with a non-existent "object_id" returns an empty list
        response = self.client.get(
            reverse("api-v2:rule-list"),
            {"object_id": "-1"},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)

        # Check retrieving rules whose "enabled" is "true"
        expected = tests.Data("examples", "rest.rule.filter_by_enabled.json").json()
        response = self.client.get(
            reverse("api-v2:rule-list"),
            {"enabled": "true"},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # Check retrieving rules whose "parent" is "Test Rule"
        expected = tests.Data("examples", "rest.rule.filter_by_parent.json").json()
        response = self.client.get(
            reverse("api-v2:rule-list"),
            {"parent": "Test Rule"},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # Check retrieving rules with a non-existent "parent" returns an empty list
        response = self.client.get(
            reverse("api-v2:rule-list"),
            {"parent": "-1"},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)

        # Check retrieving rule's details without token returns 401 Unauthorized
        response = self.client.get(
            reverse("api-v2:rule-detail", args=[-1]),
        )
        self.assertEqual(response.status_code, 401)

        # Check retrieving rule's details with a non-existent "id" returns 404 Not Found
        response = self.client.get(
            reverse("api-v2:rule-detail", args=[-1]),
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 404)

        # Check retrieving rule's details with an existing "id" returns the expected rule
        expected = tests.Data("examples", "rest.rule.detail.json").json()
        response = self.client.get(
            reverse("api-v2:rule-detail", args=[1]),
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)

        # Check update a rule without token returns 401 Unauthorized
        response = self.client.put(
            reverse("api-v2:rule-detail", args=[1]),
            {
                "annotations": {"summary": "Test Rule Summary"},
                "clause": "up == 1",
                "description": "Test Rule Description",
                "duration": "5m",
                "enabled": False,
                "labels": {"severity": "critical"},
                "name": "TestRuleUpdated",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

        # Check update a rule without permission returns 403 Forbidden
        response = self.client.put(
            reverse("api-v2:rule-detail", args=[1]),
            {
                "annotations": {"summary": "Test Rule Summary"},
                "clause": "up == 1",
                "description": "Test Rule Description",
                "duration": "5m",
                "enabled": False,
                "labels": {"severity": "critical"},
                "name": "TestRuleUpdated",
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 403)

        # Check partial update a rule without token returns 401 Unauthorized
        response = self.client.patch(
            reverse("api-v2:rule-detail", args=[2]),
            {"enabled": True},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

        # Check partial update a rule without permission returns 403 Forbidden
        response = self.client.patch(
            reverse("api-v2:rule-detail", args=[2]),
            {"enabled": True},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 403)

        # Check delete a rule without token returns 401 Unauthorized
        response = self.client.delete(
            reverse("api-v2:rule-detail", args=[1]),
        )
        self.assertEqual(response.status_code, 401)

        # Check delete a rule without permission returns 403 Forbidden
        response = self.client.delete(
            reverse("api-v2:rule-detail", args=[1]), HTTP_AUTHORIZATION=f"Token {token}"
        )
        self.assertEqual(response.status_code, 403)

        user = User.objects.get(username="demo")
        user.user_permissions.add(Permission.objects.get(codename="change_rule"))
        user.user_permissions.add(Permission.objects.get(codename="delete_rule"))

        # Check update a rule successfully with permission
        expected = tests.Data("examples", "rest.rule.update.json").json()
        response = self.client.put(
            reverse("api-v2:rule-detail", args=[1]),
            {
                "annotations": {"summary": "Test Rule Summary"},
                "clause": "up == 1",
                "description": "Test Rule Description",
                "duration": "5m",
                "enabled": False,
                "labels": {"severity": "critical"},
                "name": "TestRuleUpdated",
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # Check partial update a rule successfully with permission
        expected = tests.Data("examples", "rest.rule.partial_update.json").json()
        response = self.client.patch(
            reverse("api-v2:rule-detail", args=[2]),
            {"enabled": True},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # Check delete a rule successfully with permission
        response = self.client.delete(
            reverse("api-v2:rule-detail", args=[1]), HTTP_AUTHORIZATION=f"Token {token}"
        )
        self.assertEqual(response.status_code, 204)
