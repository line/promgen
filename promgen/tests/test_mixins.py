# Copyright (c) 2025 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE
from unittest.mock import patch

from django.contrib.auth.models import Permission
from django.shortcuts import get_object_or_404
from django.test import RequestFactory
from guardian.shortcuts import assign_perm

from promgen import models, tests
from promgen.mixins import PromgenGuardianPermissionMixin


class MockView(PromgenGuardianPermissionMixin):
    def get_object(self):
        return self.object

    def dispatch(self, request, *args, **kwargs):
        self.request = request
        response = self.check_permissions(request)
        if response:
            return "Permission Denied"
        return "Permission Granted"


class PromgenGuardianPermissionMixinTest(tests.PromgenTest):
    def setUp(self):
        self.view = MockView()
        factory = RequestFactory()
        self.request = factory.get("/")

    def test_permission_granted(self):
        user = self.force_login(username="demo")
        object = get_object_or_404(models.Project, pk=1)
        permission_required = Permission.objects.get(
            codename="project_admin", content_type__model="project"
        )
        assign_perm(permission_required, user, object)
        self.view.permission_required = permission_required.codename
        self.view.object = object
        self.request.user = user
        response = self.view.dispatch(self.request)
        self.assertEqual(response, "Permission Granted")

    @patch("django.contrib.messages.api.add_message")
    def test_permission_not_granted(self, mock_add_message):
        user = self.force_login(username="demo")
        object = get_object_or_404(models.Project, pk=1)
        permission_required = Permission.objects.get(
            codename="project_admin", content_type__model="project"
        )
        self.view.permission_required = permission_required.codename
        self.view.object = object
        self.request.user = user
        response = self.view.dispatch(self.request)
        self.assertEqual(response, "Permission Denied")

    def test_permission_granted_on_parent_object(self):
        user = self.force_login(username="demo")
        object = get_object_or_404(models.Service, pk=1)
        permission_required = Permission.objects.get(
            codename="service_admin", content_type__model="service"
        )
        assign_perm(permission_required, user, object)
        self.view.permission_required = permission_required.codename
        self.view.object = object
        self.request.user = user
        response = self.view.dispatch(self.request)
        self.assertEqual(response, "Permission Granted")

    @patch("django.contrib.messages.api.add_message")
    def test_permission_granted_on_another_object(self, mock_add_message):
        user = self.force_login(username="demo")
        object = get_object_or_404(models.Service, pk=1)
        another_object = models.Service.objects.create(name="Another Service", owner=user)
        permission_required = Permission.objects.get(
            codename="service_admin", content_type__model="service"
        )
        assign_perm(permission_required, user, another_object)
        self.view.permission_required = permission_required.codename
        self.view.object = object
        self.request.user = user
        response = self.view.dispatch(self.request)
        self.assertEqual(response, "Permission Denied")
