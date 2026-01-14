# Copyright (c) 2019 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404
from django.views.generic.base import ContextMixin
from django.views.generic.edit import FormView

from promgen import forms, models, notification


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


class NotifierFormMixin(FormView):
    model = models.Sender
    form_class = forms.SenderForm

    def post(self, request, *args, **kwargs):
        notifier_form = notification.load(request.POST["sender"]).form(request.POST)
        if notifier_form.is_valid():
            data = request.POST.copy()
            data.update(notifier_form.cleaned_data)
            sender_form = self.form_class(data)
            if sender_form.is_valid():
                return self.form_valid(sender_form)
            else:
                return self.form_invalid(sender_form)
        return self.form_invalid(notifier_form)
