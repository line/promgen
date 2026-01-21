# Copyright (c) 2022 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE
from django.urls import reverse

from promgen import models, tests, views


class WebTests(tests.PromgenTest):
    fixtures = ["testcases.yaml", "extras.yaml"]

    route_map = [
        # viewname, viewclass, extra params
        ("datasource-list", views.DatasourceList, {}),
        ("datasource-detail", views.DatasourceDetail, {"pk": 1}),
        ("service-list", views.ServiceList, {}),
        ("service-detail", views.ServiceDetail, {"pk": 1}),
        ("project-detail", views.ProjectDetail, {"pk": 1}),
        ("project-exporter", views.ExporterRegister, {"pk": 1}),
        ("project-notifier", views.ProjectNotifierRegister, {"pk": 1}),
        ("url-list", views.URLList, {}),
        ("farm-list", views.FarmList, {}),
        ("farm-detail", views.FarmDetail, {"pk": 1}),
        ("host-list", views.HostList, {}),
        ("host-detail", views.HostDetail, {"slug": "example.com"}),
        ("rules-list", views.RulesList, {}),
        ("rule-detail", views.RuleDetail, {"pk": 1}),
        ("audit-list", views.AuditList, {}),
        ("site-detail", views.SiteDetail, {}),
        ("profile", views.Profile, {}),
        # For this test, we're testing a non-admin user
        # so we expect this page to redirect to 302
        ("import", views.Import, {"status_code": 302}),
        ("alert-list", views.AlertList, {}),
        ("alert-detail", views.AlertDetail, {"pk": 1}),
        ("metrics", views.Metrics, {}),
    ]

    def setUp(self):
        self.user = self.force_login(username="demo")

    def test_routes(self):
        for viewname, viewclass, params in self.route_map:
            # By default we'll pass all params as-is to our reverse()
            # method, but we may have a few special ones (like status_code)
            # that we want to pop and handle separately
            # Default to checking for a 200 unless we need to specifically
            # check for a redirect or some other status code.
            status_code = params.pop("status_code", 200)
            with self.subTest(viewname=viewname, params=params):
                response = self.client.get(reverse(viewname, kwargs=params))
                self.assertRoute(response, viewclass, status_code)

    def test_delete_project_without_farm(self):
        # Create a project without associating it with a farm
        shard = models.Shard.objects.get(pk=1)
        service = models.Service.objects.get(pk=1)
        project = models.Project.objects.create(
            name="test delete project",
            owner=self.user,
            service=service,
            shard=shard,
        )

        self.assertFalse(hasattr(project, "farm"))

        # Attempt to delete the project
        response = self.client.post(reverse("project-delete", kwargs={"pk": project.pk}))

        # Assert the project is deleted successfully
        self.assertEqual(response.status_code, 302)
        self.assertFalse(models.Project.objects.filter(pk=project.pk).exists())

    def test_merge_users(self):
        from django.contrib.auth.models import User
        from guardian.models import UserObjectPermission
        from guardian.shortcuts import assign_perm
        from social_django.models import UserSocialAuth

        from promgen.notification.email import NotificationEmail
        from promgen.notification.user import NotificationUser

        test_shard = models.Shard.objects.get(pk=1)
        test_service = models.Service.objects.get(pk=1)

        user_to_merge_from = User.objects.create_user(username="user_to_merge_from")
        user_to_merge_into = User.objects.create_user(username="user_to_merge_into")
        social_auth = UserSocialAuth.objects.create(
            provider="github",
            uid="12345",
            user=user_to_merge_from,
        )

        service = models.Service.objects.create(name="Service", owner=user_to_merge_from)
        project = models.Project.objects.create(
            name="Project", owner=user_to_merge_from, service=service, shard=test_shard
        )
        sender_email = NotificationEmail.create(
            obj=service, value="example@example.com", owner=user_to_merge_from
        )
        sender_user = NotificationUser.create(
            obj=service, value=user_to_merge_from.pk, owner=user_to_merge_from
        )
        assign_perm("service_viewer", user_to_merge_from, test_service)

        group = models.Group.objects.create(name="Test Group")
        user_to_merge_from.groups.add(group)
        assign_perm("group_admin", user_to_merge_from, group)
        assign_perm("group_member", user_to_merge_into, group)

        self.force_login(username="admin")
        response = self.client.post(
            reverse("admin:user-merge"),
            {
                "user_to_merge_from": user_to_merge_from.username,
                "user_to_merge_into": user_to_merge_into.username,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            reverse("admin:auth_user_changelist"),
            "Redirected back to user changelist after merge",
        )

        social_auth.refresh_from_db()
        service.refresh_from_db()
        project.refresh_from_db()
        sender_email.refresh_from_db()
        sender_user.refresh_from_db()

        self.assertTrue(
            social_auth.user == user_to_merge_into,
            "Social auth transferred to the user to merge into",
        )
        self.assertTrue(
            service.owner == user_to_merge_into, "Service owner changed to the user to merge into"
        )
        self.assertTrue(
            project.owner == user_to_merge_into, "Project owner changed to the user to merge into"
        )
        self.assertTrue(
            sender_email.owner == user_to_merge_into,
            "Sender owner changed to the user to merge into",
        )
        self.assertTrue(
            sender_user.owner == user_to_merge_into,
            "Sender owner changed to the user to merge into",
        )
        self.assertTrue(
            sender_user.value == str(user_to_merge_into.pk),
            "Sender value changed to the user to merge into",
        )
        self.assertEqual(
            UserObjectPermission.objects.filter(
                user=user_to_merge_into,
                object_pk=service.pk,
                content_type__app_label="promgen",
                content_type__model="service",
            ).count(),
            1,
            "New owner has only one permission on service",
        )
        self.assertTrue(
            user_to_merge_into.has_perm("service_admin", service), "New owner has ADMIN permission"
        )
        self.assertEqual(
            UserObjectPermission.objects.filter(
                user=user_to_merge_into,
                object_pk=project.pk,
                content_type__app_label="promgen",
                content_type__model="project",
            ).count(),
            1,
            "New owner has only one permission on project",
        )
        self.assertTrue(
            user_to_merge_into.has_perm("project_admin", project), "New owner has ADMIN permission"
        )
        self.assertTrue(
            user_to_merge_into.has_perm("service_viewer", test_service),
            "The user to merge into inherit existing permissions",
        )
        self.assertTrue(
            user_to_merge_into.groups.filter(pk=group.pk).exists(),
            "The user to merge into inherit group membership",
        )
        self.assertEqual(
            UserObjectPermission.objects.filter(
                user=user_to_merge_into,
                object_pk=group.pk,
                content_type__app_label="auth",
                content_type__model="group",
            ).count(),
            1,
            "New owner has only one permission on group",
        )
        self.assertTrue(
            user_to_merge_into.has_perm("group_admin", group),
            "The user to merge into inherit the highest permission on group",
        )
        self.assertFalse(
            UserObjectPermission.objects.filter(user_id=user_to_merge_from.pk).exists(),
            "The user to merge from's object permissions deleted",
        )
        self.assertFalse(
            User.objects.filter(pk=user_to_merge_from.pk).exists(),
            "The user to merge from was deleted",
        )

    def test_merge_users_no_permissions(self):
        self.force_login(username="demo")

        response = self.client.post(reverse("admin:user-merge"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            reverse("admin:login") + "?next=" + reverse("admin:user-merge"),
            "Non-admin user redirected to login page",
        )
