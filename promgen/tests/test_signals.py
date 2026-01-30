# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

from unittest import mock

from guardian.shortcuts import assign_perm, remove_perm

from promgen import models, tests
from promgen.notification.user import NotificationUser


class SignalTest(tests.PromgenTest):
    def setUp(self):
        self.user = self.force_login(username="demo")

    @mock.patch("promgen.models.Audit.log")
    @mock.patch("promgen.signals.trigger_write_config.send")
    def test_write_signal(self, write_mock, log_mock):
        # Create a new project or testing
        project = models.Project.objects.create(
            name="Project", service_id=1, shard_id=1, owner=self.user
        )

        # Create a test farm
        farm = models.Farm.objects.create(name="farm", project=project)
        models.Host.objects.create(name="Host", farm=farm)

        e1 = models.Exporter.objects.create(
            job="Exporter 1",
            port=1234,
            project=project,
        )

        e2 = models.Exporter.objects.create(
            job="Exporter 2",
            port=1234,
            project=project,
        )

        # Should be called once for each created exporter
        self.assertEqual(write_mock.call_count, 2, "Two write calls")
        write_mock.assert_has_calls([mock.call(e1), mock.call(e2)])

    @mock.patch("promgen.models.Audit.log")
    @mock.patch("promgen.signals.trigger_write_config.send")
    def test_write_and_delete(self, write_mock, log_mock):
        project = models.Project.objects.create(
            name="Project", service_id=1, shard_id=1, owner=self.user
        )

        # Create a test farm
        farm = models.Farm.objects.create(name="farm", project=project)
        models.Host.objects.create(name="Host", farm=farm)

        # Farm but no exporters so no call
        self.assertEqual(write_mock.call_count, 0, "Should not be called without exporters")

        models.Exporter.objects.create(
            job="Exporter 1",
            port=1234,
            project=project,
        )
        # Create an exporter so our call should be 1
        self.assertEqual(write_mock.call_count, 1, "Should be called after creating exporter")

        farm.delete()
        # For our test case, we refresh our copy from the DB to reflect the
        # deleted farm.
        project.refresh_from_db()

        # Deleting our farm will call pre_delete on Farm and post_save on project
        self.assertEqual(write_mock.call_count, 3, "Should be called after deleting farm")

        models.Exporter.objects.create(
            job="Exporter 2",
            port=1234,
            project=project,
        )
        # Deleting our farm means our config is inactive, so no additional calls
        # from creating exporter
        self.assertEqual(
            write_mock.call_count,
            3,
            "No farms, so should not be called after deleting exporter",
        )

    @mock.patch("promgen.models.Audit.log")
    def test_check_permissions_and_unsubscribe_notification(self, log_mock):
        service = models.Service.objects.get(pk=1)
        project = service.project_set.first()
        assign_perm("project_viewer", self.user, project)
        group = models.Group.objects.create(name="Test Group")
        group.user_set.add(self.user)

        NotificationUser.create(obj=project, value=str(self.user.pk), owner=self.user)

        # User has both user and group-project permission, removing user permission should
        # keep the subscription on project
        assign_perm("project_viewer", group, project)
        remove_perm("project_viewer", self.user, project)
        self.assertEqual(
            models.Sender.objects.filter(
                obj=project, sender="promgen.notification.user", value=str(self.user.pk)
            ).count(),
            1,
            "User should remain subscribed because they still have group permission",
        )

        # User has both group-project and service permission, removing group permission should
        # keep the subscription on project
        assign_perm("service_viewer", self.user, service)
        remove_perm("project_viewer", group, project)
        self.assertEqual(
            models.Sender.objects.filter(
                obj=project, sender="promgen.notification.user", value=str(self.user.pk)
            ).count(),
            1,
            "User should remain subscribed because they still have service permission",
        )

        # User only has user permission, removing service permission should
        # remove the subscription on project
        remove_perm("service_viewer", self.user, service)
        self.assertEqual(
            models.Sender.objects.filter(
                obj=project, sender="promgen.notification.user", value=str(self.user.pk)
            ).count(),
            0,
            "User should be unsubscribed because they no longer have any permissions",
        )

    @mock.patch("promgen.models.Audit.log")
    def test_unsubscribe_when_removing_permission(self, log_mock):
        service = models.Service.objects.get(pk=1)
        project = service.project_set.first()
        group = models.Group.objects.create(name="Test Group")
        group.user_set.add(self.user)

        # 1. Check if removing user permission unsubscribes user
        assign_perm("service_viewer", self.user, service)
        NotificationUser.create(obj=service, value=str(self.user.pk), owner=self.user)
        NotificationUser.create(obj=project, value=str(self.user.pk), owner=self.user)
        remove_perm("service_viewer", self.user, service)

        self.assertEqual(
            models.Sender.objects.filter(
                obj=service, sender="promgen.notification.user", value=str(self.user.pk)
            ).count(),
            0,
            "User should be unsubscribed service when permissions are removed",
        )

        self.assertEqual(
            models.Sender.objects.filter(
                obj=project, sender="promgen.notification.user", value=str(self.user.pk)
            ).count(),
            0,
            "User should be unsubscribed project too, because they only had permission on service",
        )

        # 2. Check if removing group permission unsubscribes user
        assign_perm("service_viewer", group, service)
        # Re-subscribe
        NotificationUser.create(obj=service, value=str(self.user.pk), owner=self.user)
        remove_perm("service_viewer", group, service)

        self.assertEqual(
            models.Sender.objects.filter(
                obj=service, sender="promgen.notification.user", value=str(self.user.pk)
            ).count(),
            0,
            "User should be unsubscribed service when permissions are removed",
        )

    @mock.patch("promgen.models.Audit.log")
    def test_unsubscribe_when_removing_user_from_group(self, log_mock):
        service = models.Service.objects.get(pk=1)
        group = models.Group.objects.create(name="Test Group")

        group.user_set.add(self.user)
        assign_perm("service_viewer", group, service)
        NotificationUser.create(obj=service, value=str(self.user.pk), owner=self.user)
        group.user_set.remove(self.user)

        self.assertEqual(
            models.Sender.objects.filter(
                obj=service, sender="promgen.notification.user", value=str(self.user.pk)
            ).count(),
            0,
            "User should be unsubscribed service when user is removed from group",
        )

    @mock.patch("promgen.models.Audit.log")
    def test_unsubscribe_when_project_change_service(self, log_mock):
        service = models.Service.objects.get(pk=1)
        other_service = models.Service.objects.get(pk=2)
        project = service.project_set.first()

        # Check if changing project service unsubscribes user
        # if they don't have permission on the new service
        NotificationUser.create(obj=project, value=str(self.user.pk), owner=self.user)
        project.service = other_service
        project.save()

        self.assertEqual(
            models.Sender.objects.filter(
                obj=project, sender="promgen.notification.user", value=str(self.user.pk)
            ).count(),
            0,
            "User should be unsubscribed from project when project changes service"
            " because they don't have permission on the new service",
        )

        # Check if changing project service keeps user subscribed
        # if they have permission on the new service
        assign_perm("service_viewer", self.user, service)
        # Re-subscribe
        NotificationUser.create(obj=project, value=str(self.user.pk), owner=self.user)
        project.service = service
        project.save()

        self.assertEqual(
            models.Sender.objects.filter(
                obj=project, sender="promgen.notification.user", value=str(self.user.pk)
            ).count(),
            1,
            "User should remain subscribed from project when project changes service"
            " because they have permission on the new service",
        )
