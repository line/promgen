# Copyright (c) 2025 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE
from django.utils.itercompat import is_iterable
from rest_framework.permissions import BasePermission


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
