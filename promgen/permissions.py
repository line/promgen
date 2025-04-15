# Copyright (c) 2025 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE
from django.contrib.auth.models import User
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


def get_check_permission_objects(obj):
    # Because we only define permission codes for Service, Group, and Project,
    # we need to map other objects to these.
    if isinstance(obj, (models.Service, models.Group)):
        return [obj]
    if isinstance(obj, models.Project):
        return [obj, obj.service]
    if isinstance(obj, (models.Exporter, models.URL, models.Farm)):
        return [obj.project, obj.project.service]
    if isinstance(obj, models.Host):
        return [obj.farm.project, obj.farm.project.service]
    if isinstance(obj, (models.Rule, models.Sender)):
        content_obj = getattr(obj, "content_object", None)
        if isinstance(content_obj, models.Project):
            return [content_obj, content_obj.service]
        elif content_obj is not None:
            return [content_obj]
    return None


def has_perm(user: User, perms: list[str], obj) -> bool:
    # Superusers always have permission
    if user.is_active and user.is_superuser:
        return True

    check_permission_objects = get_check_permission_objects(obj)
    if not check_permission_objects:
        return False

    for check_obj in check_permission_objects:
        # If the check_obj is the user itself, return True.
        # Otherwise, check permissions.
        # This also returns True if the user belongs to a Group that has the permission.
        has_permission = user == check_obj or any(user.has_perm(perm, check_obj) for perm in perms)
        if has_permission:
            return True
    return False


def get_objects_for_user_with_perms(user: User, perms: list[str], klass):
    """
    Wrapper around guardian.shortcuts.get_objects_for_user to get objects
    for a user with specific permissions.

    Some important parameters are set according to Promgen's permission model:
    - any_perm=True: Return objects that match any of the specified permissions.
    - use_groups=True: Consider permissions assigned via both user and group of users.
    - accept_global_perms=False: Do not consider global permissions for objects.

    Args:
        user (User): The user for whom to retrieve objects.
        perms (list[str]): List of permission codenames to check.
        klass (Model, optional): The model class to filter objects.

    Returns:
        QuerySet: A queryset of objects the user has the specified permissions for.

    """
    return get_objects_for_user(
        user,
        perms,
        any_perm=True,
        use_groups=True,
        accept_global_perms=False,
        klass=klass,
    )


def get_accessible_services_for_user(user: User):
    return get_objects_for_user_with_perms(
        user, ["service_admin", "service_editor", "service_viewer"], klass=models.Service
    )
