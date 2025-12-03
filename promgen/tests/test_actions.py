# Copyright (c) 2024 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE
from django.contrib.auth.models import User
from django.urls import reverse
from guardian.models import UserObjectPermission
from guardian.shortcuts import assign_perm

from promgen import models, tests
from promgen.notification.email import NotificationEmail
from promgen.notification.user import NotificationUser


class ActionTests(tests.PromgenTest):
    fixtures = ["testcases.yaml", "extras.yaml"]

    def test_merge_users(self):
        test_shard = models.Shard.objects.get(pk=1)
        test_service = models.Service.objects.get(pk=1)

        old_user_1 = User.objects.create_user(username="old_user_1")
        old_user_2 = User.objects.create_user(username="old_user_2")
        new_user = User.objects.create_user(username="new_user")

        service = models.Service.objects.create(name="Service", owner=old_user_1)
        project = models.Project.objects.create(
            name="Project", owner=old_user_1, service=service, shard=test_shard
        )
        sender_email = NotificationEmail.create(
            obj=service, value="example@example.com", owner=old_user_1
        )
        sender_user = NotificationUser.create(obj=service, value=old_user_1.pk, owner=old_user_1)
        assign_perm("service_viewer", old_user_1, test_service)

        group = models.Group.objects.create(name="Test Group")
        old_user_1.groups.add(group)
        assign_perm("group_admin", old_user_1, group)
        assign_perm("group_member", old_user_2, group)

        self.force_login(username="demo")
        response = self.client.post(
            reverse("admin:auth_user_changelist"),
            {
                "action": "merge_users_action",
                "_selected_action": [old_user_1.pk, old_user_2.pk, new_user.pk],
                "new_user_id": new_user.pk,
            },
        )

        # Check non-admin user cannot perform merge action
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            reverse("admin:login") + "?next=" + reverse("admin:auth_user_changelist"),
            "Non-admin user redirected to login page",
        )

        # Check admin user can perform merge action
        self.force_login(username="admin")
        response = self.client.post(
            reverse("admin:auth_user_changelist"),
            {
                "action": "merge_users_action",
                "_selected_action": [old_user_1.pk, old_user_2.pk, new_user.pk],
                "new_user_id": new_user.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            reverse("admin:auth_user_changelist"),
            "Redirected back to user changelist after merge",
        )

        service.refresh_from_db()
        project.refresh_from_db()
        sender_email.refresh_from_db()
        sender_user.refresh_from_db()
        self.assertTrue(service.owner == new_user, "Service owner changed to new user")
        self.assertTrue(project.owner == new_user, "Project owner changed to new user")
        self.assertTrue(sender_email.owner == new_user, "Sender owner changed to new user")
        self.assertTrue(sender_user.owner == new_user, "Sender owner changed to new user")
        self.assertTrue(sender_user.value == str(new_user.pk), "Sender value changed to new user")
        self.assertEqual(
            UserObjectPermission.objects.filter(
                user=new_user,
                object_pk=service.pk,
                content_type__app_label="promgen",
                content_type__model="service",
            ).count(),
            1,
            "New owner has only one permission on service",
        )
        self.assertTrue(
            new_user.has_perm("service_admin", service), "New owner has ADMIN permission"
        )
        self.assertEqual(
            UserObjectPermission.objects.filter(
                user=new_user,
                object_pk=project.pk,
                content_type__app_label="promgen",
                content_type__model="project",
            ).count(),
            1,
            "New owner has only one permission on project",
        )
        self.assertTrue(
            new_user.has_perm("project_admin", project), "New owner has ADMIN permission"
        )
        self.assertTrue(
            new_user.has_perm("service_viewer", test_service),
            "New user inherit existing permissions",
        )
        self.assertTrue(
            new_user.groups.filter(pk=group.pk).exists(),
            "New user inherit group membership",
        )
        self.assertEqual(
            UserObjectPermission.objects.filter(
                user=new_user,
                object_pk=group.pk,
                content_type__app_label="auth",
                content_type__model="group",
            ).count(),
            1,
            "New owner has only one permission on group",
        )
        self.assertTrue(
            new_user.has_perm("group_admin", group),
            "New user inherit the highest permission on group",
        )
        self.assertFalse(
            UserObjectPermission.objects.filter(
                user_id__in=[old_user_1.pk, old_user_2.pk]
            ).exists(),
            "Old users' object permissions deleted",
        )
        self.assertFalse(User.objects.filter(pk=old_user_1.pk).exists(), "Old user 1 deleted")
        self.assertFalse(User.objects.filter(pk=old_user_2.pk).exists(), "Old user 2 deleted")
