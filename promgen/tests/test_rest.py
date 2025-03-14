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
    def test_rest_farm(self):
        token = Token.objects.filter(user__username="demo").first().key

        # Test V1 API
        expected = tests.Data("examples", "rest.farm.v1.json").json()

        # Check retrieving farms without token returns 401 Unauthorized
        response = self.client.get(reverse("api:farm-list"))
        self.assertEqual(response.status_code, 401)

        # Check retrieving all farms with token successfully
        response = self.client.get(
            reverse("api:farm-list"),
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # Check retrieving all farms whose "name" contains "farm"
        response = self.client.get(
            reverse("api:farm-list"),
            {"name": "farm"},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # Check retrieving all farms whose "source" is "promgen"
        expected = tests.Data("examples", "rest.farm.v1.filter_by_source.json").json()
        response = self.client.get(
            reverse("api:farm-list"),
            {"source": "promgen"},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # Check retrieving farms with a non-existent "name" returns an empty list
        response = self.client.get(
            reverse("api:farm-list"),
            {"name": "other-name"},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

        # Check retrieving farms with a non-existent "source" returns 400 Bad Request
        response = self.client.get(
            reverse("api:farm-list"),
            {"source": "other-source"},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 400)

        # Check retrieving the farm whose "id" is "1" without token returns 401 Unauthorized
        expected = tests.Data("examples", "rest.farm.v1.detail.json").json()
        response = self.client.get(
            reverse("api:farm-detail", args=[1]),
        )
        self.assertEqual(response.status_code, 401)

        # Check retrieving the farm whose "id" is "1", including the list of hosts.
        expected = tests.Data("examples", "rest.farm.v1.detail.json").json()
        response = self.client.get(
            reverse("api:farm-detail", args=[1]),
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # Test V2 API
        # Check retrieving all farms
        expected = tests.Data("examples", "rest.farm.default.json").json()
        response = self.client.get(reverse("api-v2:farm-list"))
        self.assertEqual(response.status_code, 401)

        # Check retrieving all farms
        expected = tests.Data("examples", "rest.farm.default.json").json()
        response = self.client.get(
            reverse("api-v2:farm-list"),
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # Check retrieving paginated farms
        expected = tests.Data("examples", "rest.farm.paginated.json").json()
        response = self.client.get(
            reverse("api-v2:farm-list"),
            {"page_number": 1, "page_size": 1},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # Check retrieving farms whose "name" contains "farm"
        expected = tests.Data("examples", "rest.farm.filter_by_name.json").json()
        response = self.client.get(
            reverse("api-v2:farm-list"),
            {"name": "test"},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # Check retrieving farms with a non-existent "name" returns an empty list
        response = self.client.get(
            reverse("api-v2:farm-list"),
            {"name": "non-existent"},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)

        # Check retrieving farms whose "source" is "promgen"
        expected = tests.Data("examples", "rest.farm.filter_by_source.json").json()
        response = self.client.get(
            reverse("api-v2:farm-list"),
            {"source": "promgen"},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # Check retrieving farms with a non-existent "source" returns 400 Bad Request
        response = self.client.get(
            reverse("api-v2:farm-list"),
            {"source": "non-existent"},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 400)

        # Check retrieving the farm whose "id" is "1"
        expected = tests.Data("examples", "rest.farm.detail.json").json()
        response = self.client.get(
            reverse("api-v2:farm-detail", args=[1]),
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # Check retrieving the list of hosts of the farm whose "id" is "1"
        expected = tests.Data("examples", "rest.farm.hosts.json").json()
        response = self.client.get(
            reverse("api-v2:farm-hosts", args=[1]),
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # Check retrieving the list of hosts of the farm
        # with a non-existent "id" returns 404 Not Found
        response = self.client.get(
            reverse("api-v2:farm-hosts", args=[-1]),
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 404)

        # Check create a farm without token returns 401 Unauthorized
        response = self.client.post(
            reverse("api-v2:farm-list"),
            {"name": "new-farm", "source": "promgen"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

        # Check create a farm without permission returns 403 Forbidden
        response = self.client.post(
            reverse("api-v2:farm-list"),
            {"name": "new-farm", "source": "promgen"},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 403)

        # Check update a farm without token returns 401 Unauthorized
        response = self.client.put(
            reverse("api-v2:farm-detail", args=[1]),
            {"name": "new-name", "source": "promgen"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

        # Check update a farm without permission returns 403 Forbidden
        response = self.client.put(
            reverse("api-v2:farm-detail", args=[1]),
            {"name": "new-name", "source": "promgen"},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 403)

        # Check partial update a farm without token returns 401 Unauthorized
        response = self.client.patch(
            reverse("api-v2:farm-detail", args=[1]),
            {"name": "new-new-name"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

        farm = models.Farm.objects.get(id=1)
        models.Host.objects.create(name="host.example.com", farm=farm)
        # Check partial update a farm without permission returns 403 Forbidden
        response = self.client.patch(
            reverse("api-v2:farm-detail", args=[1]),
            {"name": "new-new-name"},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 403)

        # Check register hosts for a farm without token returns 401 Unauthorized
        response = self.client.post(
            reverse("api-v2:farm-hosts", args=[1]),
            {"hosts": ["new-host", "new-host-2"]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

        # Check register hosts for a farm without permission returns 403 Forbidden
        response = self.client.post(
            reverse("api-v2:farm-hosts", args=[1]),
            {"hosts": ["new-host", "new-host-2"]},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 403)

        # Check delete hosts for a farm without token returns 401 Unauthorized
        response = self.client.delete(
            reverse("api-v2:farm-delete-host", args=[1, 2]),
        )
        self.assertEqual(response.status_code, 401)

        # Check delete hosts for a farm without permission returns 403 Forbidden
        response = self.client.delete(
            reverse("api-v2:farm-delete-host", args=[1, 2]),
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 403)

        # Check delete a farm without token returns 401 Unauthorized
        response = self.client.delete(reverse("api-v2:farm-detail", args=[1]))
        self.assertEqual(response.status_code, 401)

        # Check delete a farm without permission returns 403 Forbidden
        response = self.client.delete(
            reverse("api-v2:farm-detail", args=[1]), HTTP_AUTHORIZATION=f"Token {token}"
        )
        self.assertEqual(response.status_code, 403)

        user = User.objects.get(username="demo")
        user.user_permissions.add(Permission.objects.get(codename="add_farm"))
        user.user_permissions.add(Permission.objects.get(codename="change_farm"))
        user.user_permissions.add(Permission.objects.get(codename="delete_farm"))

        # Check create a farm successfully with permission
        expected = tests.Data("examples", "rest.farm.create.json").json()
        before_count = models.Farm.objects.count()
        response = self.client.post(
            reverse("api-v2:farm-list"),
            {"name": "new-farm", "source": "promgen"},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        after_count = models.Farm.objects.count()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(before_count + 1, after_count)
        # skip comparing the ID
        # and make sure the rest of the input from the request is the same as the output
        expected.pop("id", None)
        response.json().pop("id", None)
        self.assertEqual(response.json(), expected)

        # Check update a farm successfully with permission
        expected = tests.Data("examples", "rest.farm.update.json").json()
        response = self.client.put(
            reverse("api-v2:farm-detail", args=[1]),
            {"name": "new-name", "source": "new-source"},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # Check partial update a farm successfully with permission
        expected = tests.Data("examples", "rest.farm.partial_update.json").json()
        response = self.client.patch(
            reverse("api-v2:farm-detail", args=[1]),
            {"name": "new-new-name"},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # Check register hosts for a farm successfully with permission
        response = self.client.post(
            reverse("api-v2:farm-hosts", args=[1]),
            {"hosts": ["new-host", "new-host-2"]},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 201)

        # Check delete hosts for a farm successfully with permission
        response = self.client.delete(
            reverse("api-v2:farm-delete-host", args=[1, 2]),
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 204)

        # Check delete a farm successfully with permission
        response = self.client.delete(
            reverse("api-v2:farm-detail", args=[1]),
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 204)

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

    @override_settings(PROMGEN=tests.SETTINGS)
    def test_rest_exporter(self):
        token = Token.objects.filter(user__username="demo").first().key

        # Check retrieving exporters without token returns 401 Unauthorized
        response = self.client.get(reverse("api-v2:exporter-list"))
        self.assertEqual(response.status_code, 401)

        # Check retrieving all exporters
        expected = tests.Data("examples", "rest.exporter.default.json").json()
        response = self.client.get(
            reverse("api-v2:exporter-list"),
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # Check retrieving paginated exporters
        expected = tests.Data("examples", "rest.exporter.paginated.json").json()
        response = self.client.get(
            reverse("api-v2:exporter-list"),
            {"page_number": 1, "page_size": 1},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # Check retrieving exporters whose "enabled" is "true"
        expected = tests.Data("examples", "rest.exporter.filter_by_enabled.json").json()
        response = self.client.get(
            reverse("api-v2:exporter-list"),
            {"enabled": "true"},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # Check retrieving exporters whose "job" contains "inx"
        expected = tests.Data("examples", "rest.exporter.filter_by_job.json").json()
        response = self.client.get(
            reverse("api-v2:exporter-list"),
            {"job": "inx"},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # Check retrieving exporters with a non-existent "job" returns an empty list
        response = self.client.get(
            reverse("api-v2:exporter-list"),
            {"job": "non-existent"},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)

        # Check retrieving exporters whose "path" contains "metrics"
        expected = tests.Data("examples", "rest.exporter.filter_by_path.json").json()
        response = self.client.get(
            reverse("api-v2:exporter-list"),
            {"path": "/metrics"},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # Check retrieving exporters with a non-existent "path" returns an empty list
        response = self.client.get(
            reverse("api-v2:exporter-list"),
            {"path": "non-existent"},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)

        # Check retrieving exporters whose "project" contains "test"
        expected = tests.Data("examples", "rest.exporter.filter_by_project.json").json()
        response = self.client.get(
            reverse("api-v2:exporter-list"),
            {"project": "test"},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # Check retrieving exporters with a non-existent "project" returns an empty list
        response = self.client.get(
            reverse("api-v2:exporter-list"),
            {"project": "non-existent"},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)

        # Check retrieving exporters whose "scheme" is "http"
        expected = tests.Data("examples", "rest.exporter.filter_by_scheme.json").json()
        response = self.client.get(
            reverse("api-v2:exporter-list"),
            {"scheme": "https"},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # Check retrieving exporters with a non-existent "scheme" returns an 400 Bad Request
        response = self.client.get(
            reverse("api-v2:exporter-list"),
            {"scheme": "non-existent"},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 400)

        # Check retrieving exporters whose "id" is "1" without token returns 401 Unauthorized
        response = self.client.get(reverse("api-v2:exporter-detail", args=[1]))
        self.assertEqual(response.status_code, 401)

        # Check retrieving exporters whose "id" is "1"
        expected = tests.Data("examples", "rest.exporter.detail.json").json()
        response = self.client.get(
            reverse("api-v2:exporter-detail", args=[1]),
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # Check retrieving exporters with a non-existent "id" returns 404 Not Found
        response = self.client.get(
            reverse("api-v2:exporter-detail", args=[-1]),
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 404)

    @override_settings(PROMGEN=tests.SETTINGS)
    def test_rest_url(self):
        token = Token.objects.filter(user__username="demo").first().key

        # Check retrieving urls without token returns 401 Unauthorized
        response = self.client.get(reverse("api-v2:url-list"))
        self.assertEqual(response.status_code, 401)

        # Check retrieving all urls
        expected = tests.Data("examples", "rest.url.default.json").json()
        response = self.client.get(
            reverse("api-v2:url-list"),
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # Check retrieving paginated urls
        expected = tests.Data("examples", "rest.url.paginated.json").json()
        response = self.client.get(
            reverse("api-v2:url-list"),
            {"page_number": 2, "page_size": 1},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # Check retrieving urls whose "probe" is "fixture_test"
        expected = tests.Data("examples", "rest.url.filter_by_probe.json").json()
        response = self.client.get(
            reverse("api-v2:url-list"),
            {"probe": "fixture_test"},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # Check retrieving urls with a non-existent "probe" returns 400 Bad Request
        response = self.client.get(
            reverse("api-v2:url-list"),
            {"probe": "non-existent"},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 400)

        # Check retrieving urls whose "project" contains "test"
        expected = tests.Data("examples", "rest.url.filter_by_project.json").json()
        response = self.client.get(
            reverse("api-v2:url-list"),
            {"project": "test"},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # Check retrieving urls with a non-existent "project" returns an empty list
        response = self.client.get(
            reverse("api-v2:url-list"),
            {"project": "non-existent"},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)

        # Check retrieving urls whose "id" is "1" without token returns 401 Unauthorized
        response = self.client.get(reverse("api-v2:url-detail", args=[1]))
        self.assertEqual(response.status_code, 401)

        # Check retrieving urls whose "id" is "1"
        expected = tests.Data("examples", "rest.url.detail.json").json()
        response = self.client.get(
            reverse("api-v2:url-detail", args=[1]),
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)
