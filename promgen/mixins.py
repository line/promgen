# Copyright (c) 2019 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404
from django.views.generic.base import ContextMixin

from promgen import models


class ContentTypeMixin:
    def set_object(self, content_type, object_id):
        self.content_type = ContentType.objects.get(
            model=content_type, app_label="promgen"
        )
        self.object_id = object_id


class ContentFormMixin:
    def post(self, request, content_type, object_id):
        form = self.get_form()
        # Set an instance of our service here so that we can pass it
        # along for promtool to render
        form.instance.set_object(content_type, object_id)
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


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
