# Copyright (c) 2025 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE
from rest_framework import permissions
from rest_framework.permissions import BasePermission


class ReadOnlyForAuthenticatedUserOrIsSuperuser(BasePermission):
    """
    Custom permission to only allow read-only access for authenticated users
    and full access for superusers.
    """

    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True
        return bool(
            request.user
            and request.user.is_authenticated
            and request.method in permissions.SAFE_METHODS
        )
