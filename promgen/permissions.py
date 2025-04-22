# Copyright (c) 2025 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils.itercompat import is_iterable
from guardian.shortcuts import get_objects_for_user
from rest_framework import permissions
from rest_framework.permissions import BasePermission

from promgen import models


class PromgenModelPermissions(BasePermission):
    """
    Custom permission class to check if a user has specific permissions.

    This class uses the following parameters:
        permissions_required: list[str]
            Permissions to check in the format "<app_label>.<permission codename>".
            Required.
        any_perm: bool
            Whether any of the permissions in the sequence is accepted.
            Default is False.

    Example:
        ```python
        from promgen.permissions import PromgenModelPermissions

        class MyViewSet(viewsets.ModelViewSet):
            ...
            permission_classes = [PromgenModelPermissions]
            permissions_required = ["promgen.view_model", "promgen.change_model"]
            any_perm = True
            ...
        ```
    """

    def has_permission(self, request, view):
        if not bool(request.user and request.user.is_authenticated):
            return False

        perm_list = view.permissions_required
        if not is_iterable(perm_list):
            raise ValueError("perm_list must be an iterable of permissions.")
        any_perm = getattr(view, "any_perm", False)
        if any_perm:
            return any(request.user.has_perm(perm) for perm in perm_list)
        else:
            return all(request.user.has_perm(perm) for perm in perm_list)


class ReadOnlyForAuthenticatedUserOrIsSuperuser(BasePermission):
    """
    Customize Django REST Framework's base permission class to only allow read-only access for
    authenticated users and full access for superusers.
    """

    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True
        return bool(
            request.user
            and request.user.is_authenticated
            and request.method in permissions.SAFE_METHODS
        )


def get_accessible_services_for_user(user: User):
    return get_objects_for_user(
        user,
        ["service_admin", "service_editor", "service_viewer"],
        any_perm=True,
        use_groups=True,
        accept_global_perms=False,
        klass=models.Service,
    )


def get_accessible_projects_for_user(user: User):
    services = get_accessible_services_for_user(user)
    projects = get_objects_for_user(
        user,
        ["project_admin", "project_editor", "project_viewer"],
        any_perm=True,
        use_groups=True,
        accept_global_perms=False,
        klass=models.Project,
    )
    return models.Project.objects.filter(Q(pk__in=projects) | Q(service__in=services))
