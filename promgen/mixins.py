# Copyright (c) 2019 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE
import guardian.mixins
import guardian.utils
from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.models import User
from django.contrib.auth.views import redirect_to_login
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404, redirect
from django.views.generic.base import ContextMixin

from promgen import models, views


class ContentTypeMixin:
    def set_object(self, content_type, object_id):
        self.content_type = ContentType.objects.get(model=content_type, app_label="promgen")
        self.object_id = object_id


class RuleFormMixin:
    # When creating a single object, we want to use the
    # default form class and delegate to form_valid but
    # when we are importing multiple objects, we delegate
    # a form_import class to handle processing
    def post(self, request, content_type, object_id):
        single = self.get_form(self.form_class)
        # Set an instance of our content_object here so that we can
        # pass it along for promtool to render
        single.instance.set_object(content_type, object_id)
        if single.is_valid():
            return self.form_valid(single)

        importer = self.get_form(self.form_import_class)
        if importer.is_valid():
            ct = ContentType.objects.get_by_natural_key("promgen", content_type).model_class()
            content_object = ct.objects.get(pk=object_id)

            return self.form_import(importer, content_object)

        return self.form_invalid(single)


class PromgenPermissionMixin(PermissionRequiredMixin):
    def handle_no_permission(self):
        messages.warning(self.request, self.get_permission_denied_message())
        return redirect_to_login(
            self.request.get_full_path(),
            self.get_login_url(),
            self.get_redirect_field_name(),
        )


class ShardMixin(ContextMixin):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if "pk" in self.kwargs:
            context["object"] = context["shard"] = get_object_or_404(
                models.Shard, id=self.kwargs["pk"]
            )
        return context


class ProjectMixin(ContextMixin):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if "pk" in self.kwargs:
            context["object"] = context["project"] = get_object_or_404(
                models.Project, id=self.kwargs["pk"]
            )
        return context


class ServiceMixin(ContextMixin):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if "pk" in self.kwargs:
            context["object"] = context["service"] = get_object_or_404(
                models.Service, id=self.kwargs["pk"]
            )
        return context


class PromgenGuardianPermissionMixin(guardian.mixins.PermissionRequiredMixin):
    def get_check_permission_object(self):
        # Override this method to return the object to check permissions for
        return self.get_object()

    def get_check_permission_objects(self):
        # We only define permission for Service/Project/Farm
        # So we need to check the permission for the parent objects in other cases
        try:
            object = self.get_check_permission_object()
            if isinstance(object, models.Farm):
                return [object]
            elif isinstance(object, models.Host):
                return [object, object.farm]
            elif isinstance(object, models.Service):
                return [object]
            elif isinstance(object, models.Project):
                return [object, object.service]
            elif isinstance(object, models.Exporter) or isinstance(object, models.URL):
                return [object.project, object.project.service]
            elif isinstance(object, models.Rule) or isinstance(object, models.Sender):
                if isinstance(object.content_object, models.Project):
                    return [object.content_object, object.content_object.service]
                else:
                    return [object.content_object]
            return None
        except Exception:
            return None

    def check_permissions(self, request):
        # Always allow user to view the site rule
        if isinstance(self, views.RuleDetail) and isinstance(
            self.get_check_permission_object().content_object, models.Site
        ):
            return None

        check_permission_objects = self.get_check_permission_objects()
        if check_permission_objects is None:
            if request.user.is_active and request.user.is_superuser:
                return None
            return self.on_permission_check_fail(request, None)
        # Loop through all the objects to check permissions for
        # If any of the objects has the required permission (any_perm=True), we can proceed
        # Otherwise, we will return the forbidden response
        forbidden = None
        for obj in check_permission_objects:
            # Users always have permission on themselves
            if isinstance(obj, User) and request.user == obj:
                break

            forbidden = guardian.utils.get_40x_or_None(
                request,
                perms=self.get_required_permissions(request),
                obj=obj,
                login_url=self.login_url,
                redirect_field_name=self.redirect_field_name,
                return_403=self.return_403,
                return_404=self.return_404,
                accept_global_perms=False,
                any_perm=True,
            )
            if forbidden is None:
                break
        if forbidden:
            return self.on_permission_check_fail(request, forbidden)
        return None

    def on_permission_check_fail(self, request, response, obj=None):
        messages.warning(request, "You do not have permission to perform this action.")
        referer = request.META.get("HTTP_REFERER")
        if referer:
            return redirect(referer)
        return redirect_to_login(self.request.get_full_path())
