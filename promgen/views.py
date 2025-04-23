# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import collections
import concurrent.futures
import datetime
import json
import logging
import platform
import time
from itertools import chain

import prometheus_client
import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import EmptyPage, Paginator
from django.db.models import Count, Prefetch, Q
from django.db.utils import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _
from django.views.generic import DetailView, ListView, UpdateView, View
from django.views.generic.base import RedirectView, TemplateView
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.edit import CreateView, DeleteView, FormView
from guardian.models import GroupObjectPermission
from guardian.shortcuts import assign_perm, get_perms, remove_perm
from prometheus_client.core import CounterMetricFamily, GaugeMetricFamily
from prometheus_client.parser import text_string_to_metric_families
from rest_framework.authtoken.models import Token

import promgen.templatetags.promgen as macro
from promgen import (
    discovery,
    forms,
    mixins,
    models,
    permissions,
    plugins,
    prometheus,
    signals,
    tasks,
    util,
)
from promgen.forms import GroupMemberForm, UserPermissionForm
from promgen.mixins import PromgenGuardianPermissionMixin
from promgen.shortcuts import resolve_domain

logger = logging.getLogger(__name__)


class DatasourceList(LoginRequiredMixin, ListView):
    def get_queryset(self):
        projects = models.Project.objects.all()
        # If the user is not a superuser, we need to filter the shards by the user's permissions
        if not self.request.user.is_superuser:
            projects = permissions.get_accessible_projects_for_user(self.request.user)

        return models.Shard.objects.prefetch_related(
            Prefetch("project_set", queryset=projects),
            "project_set__service",
            "project_set__service__owner",
            "project_set__service__notifiers",
            "project_set__service__notifiers__owner",
            "project_set__service__rule_set",
            "project_set__owner",
            "project_set__farm",
            "project_set__exporter_set",
            "project_set__notifiers",
            "project_set__notifiers__owner",
            "prometheus_set",
        ).annotate(num_projects=Count("project"))


class DatasourceDetail(LoginRequiredMixin, DetailView):
    def get_queryset(self):
        projects = models.Project.objects.all()
        # If the user is not a superuser, we need to filter the shards by the user's permissions
        if not self.request.user.is_superuser:
            projects = permissions.get_accessible_projects_for_user(self.request.user)

        return models.Shard.objects.prefetch_related(
            Prefetch("project_set", queryset=projects),
            "project_set__service",
            "project_set__service__owner",
            "project_set__service__notifiers",
            "project_set__service__notifiers__owner",
            "project_set__service__notifiers__filter_set",
            "project_set__service__rule_set",
            "project_set__owner",
            "project_set__farm",
            "project_set__exporter_set",
            "project_set__notifiers",
            "project_set__notifiers__owner",
            "project_set__notifiers__filter_set",
        )


class ServiceList(LoginRequiredMixin, ListView):
    paginate_by = 20

    def get_queryset(self):
        query_set = models.Service.objects.prefetch_related(
            "rule_set",
            "rule_set__parent",
            "project_set",
            "project_set__owner",
            "project_set__shard",
            "project_set__notifiers",
            "project_set__notifiers__owner",
            "project_set__notifiers__filter_set",
            "project_set__farm",
            "project_set__exporter_set",
            "owner",
            "notifiers",
            "notifiers__owner",
            "notifiers__filter_set",
        )

        services = permissions.get_accessible_services_for_user(self.request.user)
        return query_set.filter(pk__in=services)


class HomeList(LoginRequiredMixin, ListView):
    template_name = "promgen/home.html"

    def get_queryset(self):
        # TODO: Support showing subscribed projects as well
        # Get the list of senders that a user is currently subscribed to
        senders = models.Sender.objects.filter(
            value=str(self.request.user.pk),
            sender="promgen.notification.user",
            content_type=ContentType.objects.get_for_model(models.Service),
        ).values_list("object_id")

        # and return just our list of services
        query_set = models.Service.objects.filter(pk__in=senders).prefetch_related(
            "notifiers",
            "notifiers__owner",
            "owner",
            "rule_set",
            "rule_set__parent",
            "project_set",
            "project_set__farm",
            "project_set__shard",
            "project_set__exporter_set",
            "project_set__notifiers",
            "project_set__owner",
            "project_set__notifiers__owner",
        )

        services = permissions.get_accessible_services_for_user(self.request.user)
        return query_set.filter(pk__in=services)


class HostList(LoginRequiredMixin, ListView):
    def get_queryset(self):
        query_set = models.Host.objects.prefetch_related(
            "farm",
            "farm__project",
            "farm__project__service",
        )

        # If the user is not a superuser, we need to filter the hosts by the user's permissions
        if not self.request.user.is_superuser:
            projects = permissions.get_accessible_projects_for_user(self.request.user)
            farms = models.Farm.objects.filter(project__in=projects)
            query_set = query_set.filter(farm__in=farms)

        return query_set

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["host_groups"] = collections.defaultdict(list)
        for host in context["object_list"]:
            context["host_groups"][host.name].append(host)
        context["host_groups"] = dict(context["host_groups"])
        context["host_groups"] = sorted(list(context["host_groups"].items()))

        paginate_by = 50
        page_number = self.request.GET.get("page", 1)
        paginator = Paginator(context["host_groups"], paginate_by).page(page_number)
        context["host_groups"] = paginator
        return context


class HostDetail(LoginRequiredMixin, View):
    def get(self, request, slug):
        context = {}
        context["slug"] = self.kwargs["slug"]

        hosts = models.Host.objects.filter(name__icontains=self.kwargs["slug"]).prefetch_related(
            "farm"
        )

        # If the user is not a superuser, we need to filter the hosts by the user's permissions
        if not self.request.user.is_superuser:
            projects = permissions.get_accessible_projects_for_user(self.request.user)
            farms = models.Farm.objects.filter(project__in=projects)
            hosts = hosts.filter(farm__in=farms)

        context["host_list"] = hosts

        if not context["host_list"]:
            return render(request, "promgen/host_404.html", context, status=404)

        farms = models.Farm.objects.filter(
            id__in=context["host_list"].values_list("farm_id", flat=True)
        )

        projects = models.Project.objects.filter(
            id__in=farms.values_list("project__id", flat=True)
        ).prefetch_related("notifiers", "rule_set")

        exporters = models.Exporter.objects.filter(
            project_id__in=projects.values_list("id", flat=True)
        ).prefetch_related("project", "project__service")

        services = models.Service.objects.filter(
            id__in=projects.values_list("service__id", flat=True)
        ).prefetch_related("notifiers", "rule_set")

        rules = (
            models.Rule.objects.filter(
                Q(id__in=projects.values_list("rule_set__id"))
                | Q(id__in=services.values_list("rule_set__id"))
                | Q(id__in=models.Site.objects.get_current().rule_set.values_list("id"))
            )
            .select_related("content_type")
            .prefetch_related("content_object")
        )

        notifiers = (
            models.Sender.objects.filter(
                Q(id__in=projects.values_list("notifiers__id"))
                | Q(id__in=services.values_list("notifiers__id"))
            )
            .select_related("content_type")
            .prefetch_related("content_object")
        )

        # If the user is not a superuser, we need to filter other objects by the user's permissions
        if not self.request.user.is_superuser:
            accessible_services = permissions.get_accessible_services_for_user(self.request.user)
            accessible_projects = permissions.get_accessible_projects_for_user(self.request.user)

            projects = projects.filter(pk__in=accessible_projects)
            exporters = exporters.filter(project__in=accessible_projects)
            services = services.filter(pk__in=accessible_services)
            rules = rules.filter(
                Q(content_type__model="service", object_id__in=accessible_services)
                | Q(content_type__model="project", object_id__in=accessible_projects)
                | Q(id__in=models.Site.objects.get_current().rule_set.values_list("id"))
            )
            notifiers = notifiers.filter(
                Q(content_type__model="service", object_id__in=accessible_services)
                | Q(content_type__model="project", object_id__in=accessible_projects)
            )

        context["farm_list"] = farms
        context["project_list"] = projects
        context["exporter_list"] = exporters
        context["service_list"] = services
        context["rule_list"] = rules
        context["notifier_list"] = notifiers

        return render(request, "promgen/host_detail.html", context)


class AuditList(LoginRequiredMixin, ListView):
    model = models.Audit

    FILTERS = {
        "project": models.Project,
        "service": models.Service,
        "rule": models.Rule,
        "group": models.Group,
    }

    def get_queryset(self):
        queryset = self.model.objects.order_by("-created").prefetch_related(
            "content_object", "user"
        )

        for key in self.FILTERS:
            if key in self.request.GET:
                # Get any log entries for the object itself
                qset = Q(
                    object_id=self.request.GET[key],
                    content_type_id=ContentType.objects.get_for_model(self.FILTERS.get(key)).id,
                )

                if key in ["project", "service", "group"]:
                    # Get any log entries for the child objects of the object
                    qset |= Q(
                        parent_object_id=self.request.GET[key],
                        parent_content_type_id=ContentType.objects.get_for_model(
                            self.FILTERS.get(key)
                        ).id,
                    )
                queryset = queryset.filter(qset)
        if "user" in self.request.GET:
            queryset = queryset.filter(user_id=self.request.GET["user"])

        # If the user is not a superuser, we need to filter the audits by the user's permissions
        if not self.request.user.is_superuser:
            # Get all the services that the user has access to
            services = permissions.get_accessible_services_for_user(self.request.user)

            # Get all the projects that the user has access to
            projects = permissions.get_accessible_projects_for_user(self.request.user)

            # Get all the farm that the user has access to
            farms = models.Farm.objects.filter(project__in=projects)

            # Get all the groups that the user has access to
            groups = permissions.get_accessible_groups_for_user(self.request.user)

            # Filter the queryset by the user's permissions
            queryset = queryset.filter(
                Q(
                    content_type__model="service",
                    content_type__app_label="promgen",
                    object_id__in=services,
                )
                | Q(
                    content_type__model="project",
                    content_type__app_label="promgen",
                    object_id__in=projects,
                )
                | Q(
                    content_type__model="farm",
                    content_type__app_label="promgen",
                    object_id__in=farms,
                )
                | Q(
                    parent_content_type_id=ContentType.objects.get_for_model(models.Service).id,
                    parent_object_id__in=services,
                )
                | Q(
                    parent_content_type_id=ContentType.objects.get_for_model(models.Project).id,
                    parent_object_id__in=projects,
                )
                | Q(
                    parent_content_type_id=ContentType.objects.get_for_model(models.Farm).id,
                    parent_object_id__in=farms,
                )
                | Q(
                    content_type__model="group",
                    content_type__app_label="auth",
                    object_id__in=groups,
                )
                | Q(
                    parent_content_type_id=ContentType.objects.get_for_model(models.Group).id,
                    parent_object_id__in=groups,
                )
            )

        return queryset

    paginate_by = 50


class ServiceDetail(PromgenGuardianPermissionMixin, DetailView):
    permission_required = ["service_admin", "service_editor", "service_viewer"]
    queryset = models.Service.objects.prefetch_related(
        "rule_set",
        "notifiers",
        "notifiers__filter_set",
        "notifiers__owner",
        "project_set",
        "project_set__shard",
        "project_set__farm",
        "project_set__exporter_set",
        "project_set__notifiers",
        "project_set__notifiers__owner",
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["permission_form"] = UserPermissionForm(input_object=self.object)
        return context


class ServiceDelete(PromgenGuardianPermissionMixin, DeleteView):
    permission_required = ["service_admin"]
    model = models.Service

    def get_success_url(self):
        return reverse("service-list")


class ProjectDelete(PromgenGuardianPermissionMixin, DeleteView):
    permission_required = ["service_admin", "project_admin"]
    model = models.Project

    def get_success_url(self):
        return reverse("service-detail", args=[self.object.service_id])


class NotifierUpdate(PromgenGuardianPermissionMixin, UpdateView):
    permission_required = ["service_admin", "service_editor", "project_admin", "project_editor"]
    model = models.Sender
    form_class = forms.NotifierUpdate

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()
        # For populating breadcrumb
        context[obj.content_type.model] = obj.content_object
        return context

    def escape_square_brackets(self, s):
        return s.replace("[", "\[").replace("]", "\]")

    def post(self, request, pk):
        if "filter.pk" in request.POST:
            f = models.Filter.objects.get(pk=request.POST["filter.pk"])
            f.delete()
            messages.success(
                request,
                "Removed filter {} {}".format(
                    self.escape_square_brackets(f.name),
                    self.escape_square_brackets(f.value),
                ),
            )
        if "filter.name" in request.POST:
            obj = self.get_object()
            f, created = obj.filter_set.get_or_create(
                name=request.POST["filter.name"], value=request.POST["filter.value"]
            )
            if created:
                messages.success(
                    request,
                    "Created filter {} {}".format(
                        self.escape_square_brackets(f.name),
                        self.escape_square_brackets(f.value),
                    ),
                )
            else:
                messages.warning(
                    request,
                    "Updated filter {} {}".format(
                        self.escape_square_brackets(f.name),
                        self.escape_square_brackets(f.value),
                    ),
                )
        if "next" in request.POST:
            return redirect(request.POST["next"])
        return self.get(self, request, pk)


class NotifierDelete(PromgenGuardianPermissionMixin, DeleteView):
    permission_required = ["service_admin", "service_editor", "project_admin", "project_editor"]
    model = models.Sender

    def get_success_url(self):
        if "next" in self.request.POST:
            return self.request.POST["next"]
        if hasattr(self.object.content_object, "get_absolute_url"):
            return self.object.content_object.get_absolute_url() + "#notifiers"
        return reverse("profile")


class NotifierTest(PromgenGuardianPermissionMixin, View):
    permission_required = ["service_admin", "service_editor", "project_admin", "project_editor"]

    def post(self, request, pk):
        sender = get_object_or_404(models.Sender, id=pk)
        try:
            sender.test()
        except Exception:
            messages.warning(request, "Error sending test message with " + sender.sender)
        else:
            messages.info(request, "Sent test message with " + sender.sender)

        if "next" in request.POST:
            return redirect(request.POST["next"])
        if hasattr(sender.content_object, "get_absolute_url"):
            return redirect(sender.content_object)
        return redirect("profile")

    def get_check_permission_object(self):
        return get_object_or_404(models.Sender, id=self.kwargs["pk"])


class ExporterDelete(PromgenGuardianPermissionMixin, DeleteView):
    permission_required = ["service_admin", "service_editor", "project_admin", "project_editor"]
    model = models.Exporter

    def get_success_url(self):
        return reverse("project-detail", args=[self.object.project_id]) + "#exporters"


class ExporterToggle(PromgenGuardianPermissionMixin, View):
    permission_required = ["service_admin", "service_editor", "project_admin", "project_editor"]

    def post(self, request, pk):
        exporter = get_object_or_404(models.Exporter, id=pk)
        exporter.enabled = not exporter.enabled
        exporter.save()
        signals.trigger_write_config.send(request)
        return JsonResponse({"redirect": exporter.project.get_absolute_url() + "#exporters"})

    def get_check_permission_object(self):
        return get_object_or_404(models.Exporter, id=self.kwargs["pk"])

    def on_perm_check_fail(self, request):
        messages.warning(request, "You do not have permission to perform this action.")
        return JsonResponse({"redirect": "#exporters"})


class NotifierToggle(PromgenGuardianPermissionMixin, View):
    permission_required = ["service_admin", "service_editor", "project_admin", "project_editor"]

    def post(self, request, pk):
        sender = get_object_or_404(models.Sender, id=pk)
        sender.enabled = not sender.enabled
        sender.save()
        # Redirect to current page
        return JsonResponse({"redirect": "#notifiers"})

    def get_check_permission_object(self):
        return get_object_or_404(models.Sender, id=self.kwargs["pk"])

    def on_perm_check_fail(self, request):
        messages.warning(request, "You do not have permission to perform this action.")
        return JsonResponse({"redirect": "#notifiers"})


class RuleDelete(PromgenGuardianPermissionMixin, DeleteView):
    permission_required = ["service_admin", "service_editor", "project_admin", "project_editor"]
    model = models.Rule

    def get_permission_denied_message(self):
        return "Unable to delete rule %s. User lacks permission" % self.object

    def get_permission_required(self):
        # In the case of rules, we want to make sure the user has permission
        # to delete the rule itself, but also permission to change the linked object
        self.object = self.get_object()
        obj = self.object._meta
        tgt = self.object.content_object._meta

        yield f"{obj.app_label}.delete_{obj.model_name}"
        yield f"{tgt.app_label}.change_{tgt.model_name}"

    def get_success_url(self):
        return self.object.content_object.get_absolute_url() + "#rules"


class RuleToggle(PromgenGuardianPermissionMixin, SingleObjectMixin, View):
    permission_required = ["service_admin", "service_editor", "project_admin", "project_editor"]
    model = models.Rule

    def get_permission_denied_message(self):
        return "Unable to toggle rule %s. User lacks permission" % self.object

    def post(self, request, pk):
        # Before, this is done inside the get_permission_required() function, but we changed the
        # authorization model so that the function has been removed.
        self.object = self.get_object()

        self.object.enabled = not self.object.enabled
        self.object.save()
        return JsonResponse({"redirect": self.object.content_object.get_absolute_url() + "#rules"})

    def on_perm_check_fail(self, request):
        messages.warning(request, "You do not have permission to perform this action.")
        return JsonResponse({"redirect": "#rules"})


class HostDelete(PromgenGuardianPermissionMixin, DeleteView):
    permission_required = ["project_admin", "service_admin", "project_editor", "service_editor"]
    model = models.Host

    def get_success_url(self):
        return self.object.farm.get_absolute_url()


class ProjectDetail(PromgenGuardianPermissionMixin, DetailView):
    permission_required = [
        "service_admin",
        "service_editor",
        "service_viewer",
        "project_admin",
        "project_editor",
        "project_viewer",
    ]
    queryset = models.Project.objects.prefetch_related(
        "rule_set",
        "rule_set__parent",
        "notifiers",
        "notifiers__owner",
        "shard",
        "service",
        "service__rule_set",
        "service__rule_set__parent",
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sources = models.Farm.driver_set()

        # Filter out any non-remote sources because we don't support linking local farm
        sources = [source for source in sources if source[1].remote]
        # Sort the farm sources by name alphabetically
        sources = sorted(sources, key=lambda source: (source[0]))

        context["sources"] = sources
        context["url_form"] = forms.URLForm()
        context["permission_form"] = UserPermissionForm(input_object=self.object)
        return context


class FarmList(LoginRequiredMixin, ListView):
    paginate_by = 50

    def get_queryset(self):
        query_set = models.Farm.objects.prefetch_related(
            "project",
            "host_set",
        )

        # If the user is not a superuser, we need to filter the farms by the user's permissions
        if not self.request.user.is_superuser:
            projects = permissions.get_accessible_projects_for_user(self.request.user)
            query_set = query_set.filter(project__in=projects)

        return query_set


class FarmDetail(PromgenGuardianPermissionMixin, DetailView):
    permission_required = [
        "project_admin",
        "service_admin",
        "project_editor",
        "service_editor",
        "project_viewer",
        "service_viewer",
    ]
    model = models.Farm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["permission_form"] = UserPermissionForm(input_object=self.object)
        return context


class FarmUpdate(PromgenGuardianPermissionMixin, UpdateView):
    permission_required = ["project_admin", "service_admin", "project_editor", "service_editor"]
    model = models.Farm
    button_label = _("Update Farm")
    template_name = "promgen/farm_update.html"
    form_class = forms.FarmForm

    def form_valid(self, form):
        if "owner" in form.changed_data:
            if not (
                self.request.user.is_superuser or self.request.user.id == form.initial["owner"]
            ):
                form.add_error("owner", _("You do not have permission to change the owner."))
                return self.form_invalid(form)
        farm, created = models.Farm.objects.update_or_create(
            id=self.kwargs["pk"],
            defaults=form.clean(),
        )
        return redirect("farm-detail", pk=farm.id)


class FarmDelete(PromgenGuardianPermissionMixin, RedirectView):
    permission_required = ["service_admin", "service_editor", "project_admin", "project_editor"]
    pattern_name = "farm-detail"

    def post(self, request, pk):
        farm = get_object_or_404(models.Farm, id=pk)
        farm.delete()

        return HttpResponseRedirect(request.POST.get("next", reverse("farm-list")))

    def get_check_permission_object(self):
        return get_object_or_404(models.Farm, id=self.kwargs["pk"])


class UnlinkFarm(PromgenGuardianPermissionMixin, View):
    permission_required = ["service_admin", "service_editor", "project_admin", "project_editor"]

    def post(self, request, pk):
        project = get_object_or_404(models.Project, id=pk)
        oldfarm, project.farm = project.farm, None
        project.save()
        signals.trigger_write_config.send(request)

        oldfarm.delete()

        return HttpResponseRedirect(reverse("project-detail", args=[project.id]) + "#hosts")

    def get_check_permission_object(self):
        return get_object_or_404(models.Project, id=self.kwargs["pk"])


class RulesList(LoginRequiredMixin, ListView, mixins.ServiceMixin):
    paginate_by = 50
    template_name = "promgen/rule_list.html"
    queryset = models.Rule.objects.prefetch_related("content_type", "content_object")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        site_rules = models.Rule.objects.filter(
            content_type__model="site", content_type__app_label="promgen"
        ).prefetch_related("content_object")

        service_rules = models.Rule.objects.filter(
            content_type__model="service", content_type__app_label="promgen"
        ).prefetch_related(
            "content_object",
            "content_object",
            "parent",
        )

        project_rules = models.Rule.objects.filter(
            content_type__model="project", content_type__app_label="promgen"
        ).prefetch_related(
            "content_object",
            "content_object__service",
            "content_object__service",
            "parent",
        )

        # If the user is not a superuser, we need to filter the rules by the user's permissions
        if not self.request.user.is_superuser:
            services = permissions.get_accessible_services_for_user(self.request.user)
            service_rules = service_rules.filter(object_id__in=services)

            projects = permissions.get_accessible_projects_for_user(self.request.user)
            project_rules = project_rules.filter(object_id__in=projects)

        rule_list = list(chain(site_rules, service_rules, project_rules))
        page_number = self.request.GET.get("page", 1)
        context["rule_list"] = Paginator(rule_list, self.paginate_by).page(page_number)
        context["page_obj"] = context["rule_list"]

        return context


class RulesCopy(PromgenGuardianPermissionMixin, View):
    permission_required = ["service_admin", "service_editor", "project_admin", "project_editor"]

    def post(self, request, pk):
        original = get_object_or_404(models.Rule, id=pk)
        form = forms.RuleCopyForm(request.POST)

        if form.is_valid():
            rule = original.copy_to(**form.clean())
            return HttpResponseRedirect(reverse("rule-edit", args=[rule.id]))
        else:
            return HttpResponseRedirect(reverse("service-detail", args=[pk]) + "#rules")

    def get_check_permission_object(self):
        content_type = ContentType.objects.get(
            app_label="promgen", model=self.request.POST["content_type"]
        )
        model_class = content_type.model_class()
        return model_class.objects.get(pk=self.request.POST["object_id"])


class FarmRefresh(LoginRequiredMixin, RedirectView):
    pattern_name = "farm-detail"

    def post(self, request, pk):
        farm = get_object_or_404(models.Farm, id=pk)
        # If any hosts are added or removed, then we want to
        # trigger a config refresh
        if any(farm.refresh()):
            signals.trigger_write_config.send(request)
        messages.info(request, "Refreshed hosts")
        if "next" in request.POST:
            return HttpResponseRedirect(request.POST["next"])
        # If we don't have an explicit redirect, we can redirect to the farm
        # itself
        return redirect(farm)


class FarmConvert(PromgenGuardianPermissionMixin, RedirectView):
    permission_required = ["project_admin", "service_admin", "project_editor", "service_editor"]
    pattern_name = "farm-detail"

    def post(self, request, pk):
        farm = get_object_or_404(models.Farm, id=pk)
        farm.source = discovery.FARM_DEFAULT

        try:
            farm.save()
        except IntegrityError:
            return render(
                request,
                "promgen/farm_duplicate.html",
                {
                    "pk": farm.pk,
                    "next": request.POST.get("next", reverse("farm-detail", args=[farm.pk])),
                    "farm_list": models.Farm.objects.filter(name=farm.name),
                },
            )

        return HttpResponseRedirect(
            request.POST.get("next", reverse("farm-detail", args=[farm.pk]))
        )

    def get_check_permission_object(self):
        return get_object_or_404(models.Farm, id=self.kwargs["pk"])


class FarmLink(PromgenGuardianPermissionMixin, View):
    permission_required = ["service_admin", "service_editor", "project_admin", "project_editor"]

    def get(self, request, pk, source):
        if source == discovery.FARM_DEFAULT:
            messages.error(request, "Cannot link to local farm")
            return HttpResponseRedirect(reverse("project-detail", args=[pk]) + "#hosts")

        context = {
            "source": source,
            "project": get_object_or_404(models.Project, id=pk),
            "farm_list": sorted(models.Farm.fetch(source=source)),
        }
        return render(request, "promgen/link_farm.html", context)

    def post(self, request, pk, source):
        if source == discovery.FARM_DEFAULT:
            messages.error(request, "Cannot link to local farm")
            return HttpResponseRedirect(reverse("project-detail", args=[pk]) + "#hosts")

        project = get_object_or_404(models.Project, id=pk)

        farm = models.Farm.objects.create(
            name=request.POST["farm"],
            source=source,
            project=project,
        )

        logger.info("Importing %s from %s", farm.name, source)
        farm.refresh()
        messages.info(request, "Refreshed hosts")
        return HttpResponseRedirect(reverse("project-detail", args=[project.id]) + "#hosts")

    def get_check_permission_object(self):
        return get_object_or_404(models.Project, id=self.kwargs["pk"])


class ExporterRegister(PromgenGuardianPermissionMixin, FormView, mixins.ProjectMixin):
    permission_required = ["service_admin", "service_editor", "project_admin", "project_editor"]
    model = models.Exporter
    template_name = "promgen/exporter_form.html"
    form_class = forms.ExporterForm

    def form_valid(self, form):
        project = get_object_or_404(models.Project, id=self.kwargs["pk"])
        exporter, _ = models.Exporter.objects.get_or_create(project=project, **form.clean())
        return HttpResponseRedirect(reverse("project-detail", args=[project.id]) + "#exporters")

    def get_check_permission_object(self):
        return get_object_or_404(models.Project, id=self.kwargs["pk"])


class ExporterScrape(LoginRequiredMixin, View):
    # TODO: Move to /rest/project/<slug>/scrape
    def post(self, request, pk):
        # Lookup our farm for testing
        project = get_object_or_404(models.Project, pk=pk)
        farm = getattr(project, "farm", None)

        # So we have a mutable dictionary
        data = request.POST.dict()

        # The default __metrics_path__ for Prometheus is /metrics so we need to
        # manually add it here in the case it's not set for our test
        if not data.setdefault("path", "/metrics"):
            data["path"] = "/metrics"

        def query():
            futures = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                for host in farm.host_set.all():
                    futures.append(
                        executor.submit(
                            util.scrape,
                            "{scheme}://{host}:{port}{path}".format(host=host.name, **data),
                        )
                    )
                for future in concurrent.futures.as_completed(futures):
                    try:
                        result = future.result()
                        result.raise_for_status()
                        metrics = list(text_string_to_metric_families(result.text))
                        yield (
                            result.url,
                            {
                                "status_code": result.status_code,
                                "metric_count": len(list(metrics)),
                            },
                        )
                    except ValueError as e:
                        yield result.url, f"Unable to parse metrics: {e}"
                    except requests.ConnectionError as e:
                        logger.warning("Error connecting to server")
                        yield e.request.url, "Error connecting to server"
                    except requests.RequestException as e:
                        logger.warning("Error with response")
                        yield e.request.url, str(e)
                    except Exception:
                        logger.exception("Unknown Exception")
                        yield "Unknown URL", "Unknown error"

        try:
            return JsonResponse(dict(query()))
        except Exception as e:
            return JsonResponse({"error": "Error with query %s" % e})


class URLRegister(PromgenGuardianPermissionMixin, FormView, mixins.ProjectMixin):
    permission_required = ["service_admin", "service_editor", "project_admin", "project_editor"]
    model = models.URL
    form_class = forms.URLForm

    def form_valid(self, form):
        project = get_object_or_404(models.Project, id=self.kwargs["pk"])
        url, _ = models.URL.objects.get_or_create(project=project, **form.clean())
        return HttpResponseRedirect(reverse("project-detail", args=[project.id]) + "#http-checks")

    def form_invalid(self, form):
        messages.error(self.request, form.errors.as_text())
        project = get_object_or_404(models.Project, id=self.kwargs["pk"])
        return HttpResponseRedirect(reverse("project-detail", args=[project.id]) + "#http-checks")

    def get_check_permission_object(self):
        return get_object_or_404(models.Project, id=self.kwargs["pk"])


class URLDelete(PromgenGuardianPermissionMixin, DeleteView):
    permission_required = ["service_admin", "service_editor", "project_admin", "project_editor"]
    model = models.URL

    def get_success_url(self):
        return reverse("project-detail", args=[self.object.project_id]) + "#http-checks"


class URLList(LoginRequiredMixin, ListView):
    def get_queryset(self):
        query_set = models.URL.objects.prefetch_related(
            "project",
            "project__service",
            "project__shard",
            "probe",
        )

        # If the user is not a superuser, we need to filter the URLs by the user's permissions
        if not self.request.user.is_superuser:
            projects = permissions.get_accessible_projects_for_user(self.request.user)
            query_set = query_set.filter(project__in=projects)

        return query_set


class ProjectRegister(PromgenGuardianPermissionMixin, CreateView):
    permission_required = ["service_admin", "service_editor"]
    button_label = _("Register Project")
    model = models.Project
    fields = ["name", "description", "owner", "shard"]

    def get_initial(self):
        initial = {}
        if "shard" in self.request.GET:
            initial["shard"] = get_object_or_404(models.Shard, pk=self.request.GET["shard"])
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["service"] = get_object_or_404(models.Service, id=self.kwargs["pk"])
        context["shard_list"] = models.Shard.objects.all()
        if not self.request.user.is_superuser:
            context["form"].fields.pop("owner", None)
        return context

    def post(self, request, *args, **kwargs):
        if not self.request.user.is_superuser:
            self.request.POST = request.POST.copy()
            self.request.POST["owner"] = self.request.user.pk
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.service_id = self.kwargs["pk"]
        return super().form_valid(form)

    def get_check_permission_object(self):
        return get_object_or_404(models.Service, id=self.kwargs["pk"])


class ProjectUpdate(PromgenGuardianPermissionMixin, UpdateView):
    permission_required = ["service_admin", "service_editor", "project_admin", "project_editor"]
    model = models.Project
    button_label = _("Project Update")
    template_name = "promgen/project_form.html"
    fields = ["name", "description", "owner", "service", "shard"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["service"] = self.object.service
        context["shard_list"] = models.Shard.objects.all()
        return context

    def form_valid(self, form):
        if "owner" in form.changed_data:
            if not (
                self.request.user.is_superuser or self.request.user.id == form.initial["owner"]
            ):
                form.add_error("owner", _("You do not have permission to change the owner."))
                return self.form_invalid(form)
            assign_perm("project_admin", form.cleaned_data["owner"], form.instance)
        return super().form_valid(form)


class ServiceUpdate(PromgenGuardianPermissionMixin, UpdateView):
    permission_required = ["service_admin", "service_editor"]
    button_label = _("Update Service")
    form_class = forms.ServiceUpdate
    model = models.Service

    def form_valid(self, form):
        if "owner" in form.changed_data:
            if not (
                self.request.user.is_superuser or self.request.user.id == form.initial["owner"]
            ):
                form.add_error("owner", _("You do not have permission to change the owner."))
                return self.form_invalid(form)
            assign_perm("service_admin", form.cleaned_data["owner"], form.instance)
        return super().form_valid(form)


class RuleDetail(PromgenGuardianPermissionMixin, DetailView):
    permission_required = [
        "service_admin",
        "service_editor",
        "service_viewer",
        "project_admin",
        "project_editor",
        "project_viewer",
    ]
    queryset = models.Rule.objects.prefetch_related(
        "content_object",
        "content_type",
        "overrides",
        "overrides__content_object",
        "overrides__content_type",
    )


class RuleUpdate(PromgenGuardianPermissionMixin, UpdateView):
    permission_required = ["service_admin", "service_editor", "project_admin", "project_editor"]

    queryset = models.Rule.objects.prefetch_related(
        "content_object", "overrides", "overrides__content_object"
    )
    template_name = "promgen/rule_update.html"
    form_class = forms.AlertRuleForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["macro"] = macro.EXCLUSION_MACRO
        context["rules"] = [self.object.parent] if self.object.parent else [self.object]
        # We use setdefault here, because we may have received existing forms in the case of a POST
        # that has errors to be corrected
        context.setdefault("label_form", forms.LabelFormSet(initial=self.object.labels))
        context.setdefault(
            "annotation_form", forms.AnnotationFormSet(initial=self.object.annotations)
        )
        return context

    def form_invalid(self, **kwargs):
        # Typically self.form will get a copy of self.object stored as self.form.instance, but if
        # we have an invalid form, we want to ensure a clean copy of self.object when rendering the
        # page (and we can leave the dirty copy as part of self.form.instance).
        self.object = self.get_object()
        return self.render_to_response(self.get_context_data(**kwargs))

    def post(self, request, *args, **kwargs):
        # Refresh the object to set the Rule's PK back, after setting it to 0 at the AlertRuleForm.
        # Before, this is done inside the get_permission_required() function, but we changed the
        # authorization model so that the function has been removed.
        self.object = self.get_object()

        # Save a copy of our forms into a context var that we can use
        # to re-render our form properly in case of errors
        context = {}
        context["form"] = self.get_form()
        context["label_form"] = forms.LabelFormSet(data=request.POST)
        context["annotation_form"] = forms.AnnotationFormSet(data=request.POST)

        # Before we validate the form, we also want to move our labels and annotations
        # into our rule instance, so that they can be validated in the call to promtool
        context["form"].instance.labels = context["label_form"].to_dict()
        context["form"].instance.annotations = context["annotation_form"].to_dict()

        # With our labels+annotations manually cached we can test
        if not all(
            [
                context["form"].is_valid(),
                context["label_form"].is_valid(),
                context["annotation_form"].is_valid(),
            ]
        ):
            return self.form_invalid(**context)

        return self.form_valid(context["form"])


class AlertRuleRegister(PromgenGuardianPermissionMixin, mixins.RuleFormMixin, FormView):
    permission_required = ["service_admin", "service_editor", "project_admin", "project_editor"]
    model = models.Rule
    template_name = "promgen/rule_register.html"
    form_class = forms.AlertRuleForm
    form_import_class = forms.ImportRuleForm

    def get_permission_required(self):
        # In the case of rules, we want to make sure the user has permission
        # to add the rule itself, but also permission to change the linked object
        yield "promgen.add_rule"
        yield "promgen.change_" + self.kwargs["content_type"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Set a dummy rule, so that our header/breadcrumbs render correctly
        context["rule"] = models.Rule()
        context["rule"].pk = 0
        context["rule"].set_object(self.kwargs["content_type"], self.kwargs["object_id"])
        context["macro"] = macro.EXCLUSION_MACRO
        return context

    def form_valid(self, form):
        form.instance.labels[form.instance.content_type.model] = form.instance.content_object.name
        form.instance.save()
        return HttpResponseRedirect(form.instance.get_absolute_url())

    def form_import(self, form, content_object):
        data = form.clean()
        counters = prometheus.import_rules_v2(data["rules"], content_object)
        messages.info(self.request, "Imported %s" % counters)
        return HttpResponseRedirect(content_object.get_absolute_url())

    def get_check_permission_object(self):
        id = self.kwargs["object_id"]
        model = self.kwargs["content_type"]
        models = ContentType.objects.get(app_label="promgen", model=model)
        obj = models.get_object_for_this_type(pk=id)
        return obj


class ServiceRegister(LoginRequiredMixin, CreateView):
    button_label = _("Register Service")
    model = models.Service
    fields = ["name", "description", "owner"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if not self.request.user.is_superuser:
            context["form"].fields.pop("owner", None)
        return context

    def post(self, request, *args, **kwargs):
        if not self.request.user.is_superuser:
            self.request.POST = request.POST.copy()
            self.request.POST["owner"] = self.request.user.pk
        return super().post(request, *args, **kwargs)


class FarmRegister(PromgenGuardianPermissionMixin, FormView, mixins.ProjectMixin):
    permission_required = ["service_admin", "service_editor", "project_admin", "project_editor"]
    model = models.Farm
    button_label = _("Register Farm")
    template_name = "promgen/farm_register.html"
    form_class = forms.FarmForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["host_form"] = kwargs.get("host_form", forms.HostForm())
        return context

    def form_valid(self, form):
        project = get_object_or_404(models.Project, id=self.kwargs["pk"])
        host_form = forms.HostForm(data={"hosts": self.request.POST["hosts"]})
        if not host_form.is_valid():
            return self.render_to_response(self.get_context_data(form=form, host_form=host_form))

        hostnames = set()
        for hostname in host_form.cleaned_data["hosts"]:
            hostnames.add(hostname)

        farm = models.Farm.objects.create(
            source=discovery.FARM_DEFAULT, project=project, **form.clean()
        )
        for hostname in hostnames:
            host = models.Host.objects.create(name=hostname, farm_id=farm.id)
            logger.debug("Added %s to %s", host.name, farm.name)

        return HttpResponseRedirect(project.get_absolute_url() + "#hosts")

    def get_check_permission_object(self):
        return get_object_or_404(models.Project, id=self.kwargs["pk"])


class ProjectNotifierRegister(
    PromgenGuardianPermissionMixin, mixins.NotifierFormMixin, mixins.ProjectMixin
):
    permission_required = ["service_admin", "service_editor", "project_admin", "project_editor"]
    model = models.Sender
    template_name = "promgen/notifier_form.html"

    def form_valid(self, form):
        project = get_object_or_404(models.Project, id=self.kwargs["pk"])
        sender, created = models.Sender.objects.get_or_create(
            obj=project,
            **form.clean(),
            defaults={"owner": self.request.user},
        )
        signals.check_user_subscription(models.Sender, sender, created, self.request)
        return HttpResponseRedirect(project.get_absolute_url() + "#notifiers")

    def form_invalid(self, form):
        messages.error(self.request, "Error creating notifier: %s" % form.errors.as_text())
        return super().form_invalid(form)

    def get_check_permission_object(self):
        return get_object_or_404(models.Project, id=self.kwargs["pk"])


class ServiceNotifierRegister(
    PromgenGuardianPermissionMixin, mixins.NotifierFormMixin, mixins.ServiceMixin
):
    permission_required = ["service_admin", "service_editor"]
    model = models.Sender
    template_name = "promgen/notifier_form.html"

    def form_valid(self, form):
        service = get_object_or_404(models.Service, id=self.kwargs["pk"])
        sender, created = models.Sender.objects.get_or_create(
            obj=service,
            **form.clean(),
            defaults={"owner": self.request.user},
        )
        signals.check_user_subscription(models.Sender, sender, created, self.request)
        return HttpResponseRedirect(service.get_absolute_url() + "#notifiers")

    def form_invalid(self, form):
        messages.error(self.request, "Error creating notifier: %s" % form.errors.as_text())
        return super().form_invalid(form)

    def get_check_permission_object(self):
        return get_object_or_404(models.Service, id=self.kwargs["pk"])


class SiteDetail(LoginRequiredMixin, TemplateView):
    template_name = "promgen/site_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["rule_list"] = models.Rule.objects.filter(
            content_type__model="site", content_type__app_label="promgen"
        ).prefetch_related("content_object")
        return context


class Profile(LoginRequiredMixin, mixins.NotifierFormMixin):
    template_name = "promgen/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["discovery_plugins"] = [entry for entry in plugins.discovery()]
        context["notifier_plugins"] = [entry for entry in plugins.notifications()]
        context["notifiers"] = {"notifiers": models.Sender.objects.filter(obj=self.request.user)}
        context["subscriptions"] = models.Sender.objects.filter(
            sender="promgen.notification.user", value=str(self.request.user.pk)
        )
        context["api_token"] = Token.objects.filter(user=self.request.user).first()
        return context

    def form_valid(self, form):
        sender, _ = models.Sender.objects.get_or_create(
            obj=self.request.user, owner=self.request.user, **form.clean()
        )
        return redirect("profile")

    def form_invalid(self, form):
        messages.error(self.request, "Error creating notifier: %s" % form.errors.as_text())
        return super().form_invalid(form)


class HostRegister(PromgenGuardianPermissionMixin, FormView):
    permission_required = ["project_admin", "service_admin", "project_editor", "service_editor"]
    model = models.Host
    template_name = "promgen/host_form.html"
    form_class = forms.HostForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["farm"] = get_object_or_404(models.Farm, pk=self.kwargs["pk"])
        return context

    def form_valid(self, form):
        farm = get_object_or_404(models.Farm, id=self.kwargs["pk"])
        for hostname in form.cleaned_data["hosts"]:
            host, created = models.Host.objects.get_or_create(name=hostname, farm_id=farm.id)
            if created:
                logger.debug("Added %s to %s", host.name, farm.name)

        return redirect("farm-detail", pk=farm.id)

    def get_check_permission_object(self):
        return get_object_or_404(models.Farm, id=self.kwargs["pk"])


class ApiConfig(View):
    def get(self, request):
        return HttpResponse(prometheus.render_config(), content_type="application/json")

    def post(self, request, *args, **kwargs):
        try:
            body = json.loads(request.body.decode("utf-8"))

            prometheus.import_config(body, self.request.user, **kwargs)
        except Exception as e:
            return HttpResponse(e, status=400)

        return HttpResponse("Success", status=202)


class ApiQueue(View):
    def post(self, request):
        signals.trigger_write_config.send(request)
        signals.trigger_write_rules.send(request)
        signals.trigger_write_urls.send(request)
        return HttpResponse("OK", status=202)


class _ExportRules(View):
    def format(self, rules=None, name="promgen"):
        content = prometheus.render_rules(rules)
        response = HttpResponse(content)
        response["Content-Type"] = "application/x-yaml"
        response["Content-Disposition"] = "attachment; filename=%s.rule.yml" % name
        return response


class RulesConfig(_ExportRules):
    def get(self, request):
        return self.format()


class RuleExport(_ExportRules):
    def get(self, request, content_type, object_id):
        ct = ContentType.objects.get(
            app_label="promgen", model=content_type
        ).get_object_for_this_type(pk=object_id)
        rules = models.Rule.objects.filter(obj=ct)
        return self.format(rules)


class URLConfig(View):
    def get(self, request):
        return HttpResponse(prometheus.render_urls(), content_type="application/json")

    def post(self, request):
        tasks.write_urls()
        return HttpResponse("OK", status=202)


class AlertList(LoginRequiredMixin, ListView):
    paginate_by = 20
    queryset = models.Alert.objects.order_by("-created")

    def get_queryset(self):
        qs = self.queryset
        search = self.request.GET.get("search")
        if search:
            qs = self.queryset.filter(
                Q(alertlabel__name="Service", alertlabel__value__icontains=search)
                | Q(alertlabel__name="Project", alertlabel__value__icontains=search)
                | Q(alertlabel__name="Job", alertlabel__value__icontains=search)
            )
        else:
            for key, value in self.request.GET.items():
                if key in ["page", "search"]:
                    continue
                elif key == "noSent":
                    qs = qs.filter(sent_count=0)
                elif key == "sentError":
                    qs = qs.exclude(error_count=0)
                else:
                    qs = qs.filter(alertlabel__name=key, alertlabel__value=value)

        # If the user is not a superuser, we need to filter the alerts by the user's permissions
        if not self.request.user.is_superuser:
            services = permissions.get_accessible_services_for_user(self.request.user)
            projects = permissions.get_accessible_projects_for_user(self.request.user)

            qs = qs.filter(
                Q(alertlabel__name="Service", alertlabel__value__in=services.values_list("name"))
                | Q(alertlabel__name="Project", alertlabel__value__in=projects.values_list("name"))
            )

        return qs


class AlertDetail(LoginRequiredMixin, DetailView):
    model = models.Alert

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["data"] = data["object"].json
        groupLabels = data["data"].get("groupLabels", {})
        commonLabels = data["data"].get("commonLabels", {})
        data["groupLabels"] = groupLabels
        data["otherLabels"] = {x: commonLabels[x] for x in commonLabels if x not in groupLabels}
        data["redirects"] = ["service", "project"]

        return data


class Metrics(View):
    def __init__(self):
        self.registry = prometheus_client.CollectorRegistry(auto_describe=True)
        prometheus_client.GCCollector(registry=self.registry)
        prometheus_client.PlatformCollector(registry=self.registry)
        prometheus_client.ProcessCollector(registry=self.registry)
        self.registry.register(self)

    def get(self, request, *args, **kwargs):
        return HttpResponse(
            prometheus_client.generate_latest(self.registry),
            content_type=prometheus_client.CONTENT_TYPE_LATEST,
        )

    def collect(self):
        # https://github.com/prometheus/client_python#custom-collectors
        v = GaugeMetricFamily(
            "promgen_build_info", "Promgen Information", labels=["version", "python"]
        )
        v.add_metric([settings.PROMGEN_VERSION, platform.python_version()], 1)
        yield v

        try:
            yield CounterMetricFamily(
                "promgen_alerts_processed",
                "Alerts",
                models.Alert.objects.latest("id").id,
            )
        except models.Alert.DoesNotExist:
            pass

        try:
            yield CounterMetricFamily(
                "promgen_alerts_failed",
                "Failed Alerts",
                models.AlertError.objects.latest("id").id,
            )
        except models.AlertError.DoesNotExist:
            pass

        yield GaugeMetricFamily("promgen_shards", "Registered Shards", models.Shard.objects.count())
        yield GaugeMetricFamily(
            "promgen_exporters", "Registered Exporters", models.Exporter.objects.count()
        )
        yield GaugeMetricFamily(
            "promgen_services", "Registered Services", models.Service.objects.count()
        )
        yield GaugeMetricFamily(
            "promgen_projects", "Registered Projects", models.Project.objects.count()
        )
        yield GaugeMetricFamily("promgen_rules", "Registered Rules", models.Rule.objects.count())
        yield GaugeMetricFamily("promgen_urls", "Registered URLs", models.URL.objects.count())

        # TODO Properly de-duplicate after refactoring
        yield GaugeMetricFamily(
            "promgen_hosts",
            "Registered Hosts",
            len(models.Host.objects.values("name").annotate(Count("name"))),
        )

        notifier = GaugeMetricFamily(
            "promgen_notifiers", "Registered Notifiers", labels=["type", "sender"]
        )
        for entry in models.Sender.objects.values("content_type__model", "sender").annotate(
            Count("sender"), count=Count("content_type")
        ):
            notifier.add_metric([entry["content_type__model"], entry["sender"]], entry["count"])

        yield notifier

        for metric in models.Metric.objects.prefetch_related("samples"):
            yield metric.to_metric_family()


class Search(LoginRequiredMixin, View):
    paginate_by = 20

    def get(self, request):
        MAPPING = {
            "farm_list": {
                "field": ("name__icontains",),
                "model": models.Farm,
                "prefetch": ("project", "host_set"),
                "query": ("search", "var-farm"),
            },
            "group_list": {
                "field": ("name__icontains",),
                "model": models.Group,
                "query": ("search",),
            },
            "host_list": {
                "field": ("name__icontains",),
                "model": models.Host,
                "query": ("search", "var-instance"),
            },
            "project_list": {
                "field": ("name__icontains",),
                "model": models.Project,
                "prefetch": ("service", "notifiers", "exporter_set", "notifiers__owner"),
                "query": ("search", "var-project"),
            },
            "rule_list": {
                "field": ("name__icontains", "clause__icontains"),
                "model": models.Rule,
                "prefetch": ("content_object",),
                "query": ("search",),
            },
            "service_list": {
                "field": ("name__icontains",),
                "model": models.Service,
                "prefetch": ("project_set", "rule_set", "notifiers", "notifiers__owner"),
                "query": ("search", "var-service"),
            },
        }

        # To avoid searching all object, remove empty search parameters
        # from the request query string.
        query_dict = request.GET.copy()
        for key, value in query_dict.items():
            query_dict[key] = value.strip()  # Trim whitespaces of search input

        empty_value_parameters = [key for key, value in query_dict.lists() if not any(value)]
        for empty_value_parameter in empty_value_parameters:
            del query_dict[empty_value_parameter]

        # Return a warning message if no search parameters are provided with a value.
        all_query = set().union(*(obj["query"] for obj in MAPPING.values()))
        query = all_query.intersection(query_dict.keys())
        if not query:
            messages.warning(request, _("No search parameters provided."))
            return render(request, "promgen/search.html")

        context = {}
        for target, obj in MAPPING.items():
            # If our potential search keys are not in our query string
            # then we can bail out quickly
            query = set(obj["query"]).intersection(query_dict.keys())
            if not query:
                logger.info("query for %s: <skipping>", target)
                continue
            logger.info("query for %s: %s", target, query)

            qs = obj["model"].objects
            if "prefetch" in obj:
                qs = qs.prefetch_related(*obj["prefetch"])

            # Build our OR query by combining Q lookups
            filters = None
            for var in query:
                for field in obj["field"]:
                    if filters:
                        filters |= Q(**{field: query_dict[var]})
                    else:
                        filters = Q(**{field: query_dict[var]})

            logger.info("filtering %s by %s", target, filters)

            qs = qs.filter(filters)

            # If the user is not a superuser, we need to filter the result by the user's permissions
            if not self.request.user.is_superuser:
                services = permissions.get_accessible_services_for_user(self.request.user)
                projects = permissions.get_accessible_projects_for_user(self.request.user)
                farms = models.Farm.objects.filter(project__in=projects)
                groups = permissions.get_accessible_groups_for_user(self.request.user)

                if obj["model"] == models.Service:
                    qs = qs.filter(pk__in=services)
                elif obj["model"] == models.Project:
                    qs = qs.filter(pk__in=projects)
                elif obj["model"] == models.Farm:
                    qs = qs.filter(pk__in=farms)
                elif obj["model"] == models.Host:
                    qs = qs.filter(farm__in=farms)
                elif obj["model"] == models.Group:
                    qs = qs.filter(pk__in=groups)
                elif obj["model"] == models.Rule:
                    qs = qs.filter(
                        Q(
                            content_type__model="service",
                            content_type__app_label="promgen",
                            object_id__in=services,
                        )
                        | Q(
                            content_type__model="project",
                            content_type__app_label="promgen",
                            object_id__in=projects,
                        )
                    )

            try:
                page_number = query_dict.get("page", 1)
                page_target = Paginator(qs, self.paginate_by).page(page_number)
                context[target] = page_target.object_list
                # Since we run each query separately, there are many paginator objects.
                # However, we only want to display a single navigation. Therefore, we want to use
                # the largest paginator object to render the page navigation.
                if (
                    "page_obj" not in context
                    or context["page_obj"].paginator.num_pages < page_target.paginator.num_pages
                ):
                    context["page_obj"] = page_target
            except EmptyPage:
                # If page is out of range of any paginator, deliver an empty list for target.
                context[target] = None

        return render(request, "promgen/search.html", context)


class RuleImport(mixins.PromgenPermissionMixin, FormView):
    form_class = forms.ImportRuleForm
    template_name = "promgen/rule_import.html"

    # Since rule imports can change a lot of site wide stuff we
    # require site edit permission here
    permission_required = ("promgen.change_site", "promgen.change_rule")
    permisison_denied_message = "User lacks permission to import"

    def form_valid(self, form):
        data = form.clean()
        if data.get("file_field"):
            rules = data["file_field"].read().decode("utf8")
        elif data.get("rules"):
            rules = data.get("rules")
        else:
            messages.warning(self.request, "Missing rules")
            return self.form_invalid(form)

        try:
            counters = prometheus.import_rules_v2(rules)
            messages.info(self.request, "Imported %s" % counters)
            return redirect("rule-import")
        except Exception:
            messages.error(self.request, "Error importing rules")
            return self.form_invalid(form)


class Import(mixins.PromgenPermissionMixin, FormView):
    template_name = "promgen/import_form.html"
    form_class = forms.ImportConfigForm

    # Since imports can change a lot of site wide stuff we
    # require site edit permission here
    permission_required = ("promgen.change_site", "promgen.change_rule", "promgen.change_exporter")

    permission_denied_message = "User lacks permission to import"

    def form_valid(self, form):
        data = form.clean()
        if data.get("file_field"):
            messages.info(self.request, "Importing config from file")
            config = data["file_field"].read().decode("utf8")
        elif data.get("url"):
            messages.info(self.request, "Importing config from url")
            response = util.get(data["url"])
            response.raise_for_status()
            config = response.text
        elif data.get("config"):
            messages.info(self.request, "Importing config")
            config = data["config"]
        else:
            messages.warning(self.request, "Missing config")
            return self.form_invalid(form)

        kwargs = {}
        # This also lets us catch passing an empty string to signal using
        # the shard value from the post request
        if data.get("shard"):
            kwargs["replace_shard"] = data.get("shard")

        imported, skipped = prometheus.import_config(
            json.loads(config), self.request.user, **kwargs
        )

        if imported:
            counters = {key: len(imported[key]) for key in imported}
            messages.info(self.request, "Imported %s" % counters)

        if skipped:
            counters = {key: len(skipped[key]) for key in skipped}
            messages.info(self.request, "Skipped %s" % counters)

        # If we only have a single object in a category, automatically
        # redirect to that category to make things easier to understand
        if len(imported["Project"]) == 1:
            return HttpResponseRedirect(imported["Project"][0].get_absolute_url())
        if len(imported["Service"]) == 1:
            return HttpResponseRedirect(imported["Service"][0].get_absolute_url())
        if len(imported["Shard"]) == 1:
            return HttpResponseRedirect(imported["Shard"][0].get_absolute_url())

        return redirect("service-list")


class RuleTest(LoginRequiredMixin, View):
    def post(self, request, pk):
        if pk == 0:
            rule = models.Rule()
            # In Django https://code.djangoproject.com/ticket/19580, some of the
            # foreign key checks got stricter. We sets pk to 0 here so that it passes
            # django's m2m/foreign key checks, but marks for us that it's a temporary
            # rule that doesn't actually exist.
            # We'll likely want to rework this assumption when we move to a different
            # promql check
            rule.pk = 0
            rule.set_object(request.POST["content_type"], request.POST["object_id"])
        else:
            rule = get_object_or_404(models.Rule, id=pk)

        # Default values in case we do not have a more specific content_type to test against
        expected_labels = {
            "service": set(),
            "project": set(),
        }
        unexpected_labels = collections.defaultdict(set)

        # Given our current rule, we want to see what service/project it will affect, so that we can
        # check our test query output for labels outside our expected match
        if rule.content_type.model == "service":
            # for a service rule, we expect the current service and all child projects as expected
            expected_labels["service"] = {rule.content_object.name}
            expected_labels["project"] = {
                project.name for project in rule.content_object.project_set.all()
            }

        if rule.content_type.model == "project":
            # for a project rule we expect only the current project and the parent service
            expected_labels["service"] = {rule.content_object.service.name}
            expected_labels["project"] = {rule.content_object.name}

        query = macro.rulemacro(rule, request.POST["query"])
        # Since our rules affect all servers we use Promgen's proxy-query to test our rule
        # against all the servers at once
        url = resolve_domain("proxy-query")

        logger.debug("Querying %s with %s", url, query)
        start = time.time()
        result = util.get(url, {"query": query}).json()
        result["duration"] = datetime.timedelta(seconds=(time.time() - start))
        result["query"] = query

        # TODO: This could be more robust, but for now this ensures failed queries
        # without a 'data' field get processed
        metrics = result.get("data", {}).setdefault("result", [])
        result["firing"] = len(metrics) > 0
        errors = result.setdefault("errors", {})

        for row in metrics:
            if "service" not in row["metric"] and "project" not in row["metric"]:
                errors["routing"] = (
                    "Some metrics are missing service and project labels. "
                    "Promgen will be unable to route message."
                )

            for label in expected_labels:
                if label in row["metric"]:
                    if (
                        expected_labels[label]
                        and row["metric"][label] not in expected_labels[label]
                    ):
                        unexpected_labels[label].add(row["metric"][label])

        # For each key in our unexpected_labels, we want to go through the returned
        # values and check to see if it is an expected one or not.
        for label in unexpected_labels:
            if unexpected_labels[label]:
                result["severity"] = "danger"
                errors[f"unrelated_{label}"] = (
                    f"Unrelated {label} labels found\n"
                    f"Expected: {expected_labels[label]}\n"
                    f"Found: {unexpected_labels[label]}"
                )

        # Place this at the bottom to have a query error show up as danger
        if result["status"] != "success":
            result["severity"] = "danger"
            errors["Query"] = result["error"]

        return JsonResponse(
            {request.POST["target"]: render_to_string("promgen/ajax_clause_check.html", result)}
        )


class ProfileTokenGenerate(LoginRequiredMixin, View):
    def get(self, request):
        Token.objects.filter(user=request.user).delete()
        Token.objects.create(user=request.user)
        messages.success(
            request, "New API token generated successfully for " + request.user.username
        )
        return redirect("profile")


class ProfileTokenDelete(LoginRequiredMixin, View):
    def get(self, request):
        Token.objects.filter(user=request.user).delete()
        messages.success(request, "API token deleted successfully for " + request.user.username)
        return redirect("profile")


class PermissionAssign(PromgenGuardianPermissionMixin, View):
    permission_required = ["service_admin", "project_admin"]

    def post(self, request):
        obj = self.get_object()
        permission_type = request.POST["perm-type"]
        permission = request.POST["permission"]

        if "user" == permission_type:
            user = User.objects.get_by_natural_key(request.POST["username"])

            # Prevent changing permissions for the owner of the object
            if user == obj.owner and request.POST["permission"] not in self.permission_required:
                messages.warning(
                    request,
                    _(
                        "Cannot assign permission for the owner. "
                        "The owner must have the ADMIN role."
                    ),
                )
                return redirect(request.POST["next"])

            assign_perm(permission, user, obj)
            messages.success(
                request,
                _("Assigned permission: {permission} for user: {username} on: {name}").format(
                    permission=permission, username=user.username, name=obj.name
                ),
            )
        elif "group" == permission_type:
            group = models.Group.objects.get_by_natural_key(name=request.POST["group"])
            assign_perm(permission, group, obj)
            messages.success(
                request,
                _("Assigned permission: {permission} for group: {group_name} on: {name}").format(
                    permission=permission, group_name=group.name, name=obj.name
                ),
            )
        else:
            messages.error(request, _("Invalid permission type."))

        return redirect(request.POST["next"])

    def get_object(self):
        id = self.request.POST["id"]
        model = self.request.POST["model"]
        models = ContentType.objects.get(app_label="promgen", model=model)
        obj = models.get_object_for_this_type(pk=id)
        return obj


class PermissionDelete(PromgenGuardianPermissionMixin, View):
    permission_required = ["service_admin", "project_admin"]

    def post(self, request):
        obj = self.get_object()
        permission_type = request.POST["perm-type"]

        if "user" == permission_type:
            user = User.objects.get_by_natural_key(request.POST["username"])

            # Prevent removing permissions for the owner of the object
            if user == obj.owner:
                messages.warning(
                    request,
                    _("Cannot remove permissions for the owner. Please transfer ownership first."),
                )
                return redirect(request.POST["next"])

            self.delete_perm(user)
            messages.success(
                request,
                self.build_success_message(
                    "Removed all permissions of user: {username} on: {name}"
                ).format(username=user.username, name=obj.name),
            )
        elif "group" == permission_type:
            group = models.Group.objects.get_by_natural_key(name=request.POST["group"])
            self.delete_perm(group)
            messages.success(
                request,
                self.build_success_message(
                    "Removed all permissions of group: {group_name} on: {name}"
                ).format(group_name=group.name, name=obj.name),
            )
        else:
            messages.error(request, _("Invalid permission type."))
            return redirect(request.POST["next"])

        # If the user is removing their own permission, redirect to home
        if not get_perms(self.request.user, obj):
            return redirect(reverse("home"))

        return redirect(request.POST["next"])

    def delete_perm(self, user_or_group):
        obj = self.get_object()
        permissions = get_perms(user_or_group, obj)
        for perm in permissions:
            remove_perm(perm, user_or_group, obj)

        if "on" == self.request.POST.get("remove_sub_permissions") and isinstance(
            obj, models.Service
        ):
            is_owner_transferred = False
            transferred_projects = []
            # Remove all permissions for the user on this Service's projects
            for project in obj.project_set.all():
                permissions = get_perms(user_or_group, project)
                for perm in permissions:
                    remove_perm(perm, user_or_group, project)

                # If the removed user is the owner of the Project, we need to transfer the ownership
                # to the Service's owner and assign admin permission for them.
                if isinstance(user_or_group, User) and user_or_group == project.owner:
                    assign_perm("project_admin", obj.owner, project)
                    project.owner = obj.owner
                    project.save()
                    is_owner_transferred = True
                    transferred_projects.append(project.name)

            if is_owner_transferred:
                messages.warning(
                    self.request,
                    self.build_warning_message(transferred_projects, user_or_group.username),
                )

    def get_object(self):
        id = self.request.POST["id"]
        model = self.request.POST["model"]
        models = ContentType.objects.get(app_label="promgen", model=model)
        obj = models.get_object_for_this_type(pk=id)
        return obj

    def build_success_message(self, message):
        if "on" == self.request.POST.get("remove_sub_permissions") and isinstance(
            self.get_object(), models.Service
        ):
            return _(message + " and its projects.")
        return _(message + ".")

    def build_warning_message(self, projects, previous_owner):
        """
        Builds a warning message for transferred project ownership.

        Example output:
            Transferred ownership of these projects to the parent service's owner (John Doe):
              - project A
              - project B
              - ...
              - project Z
            The previous owner (John Smith) had its permissions removed.
        """

        projects = "<ul v-pre>" + "".join(f"<li>{p}</li>" for p in projects) + "</ul>"
        msg = _(
            "Transferred ownership of these projects to the parent service's owner ({owner}):"
            + "{projects}"
            + "The previous owner ({previous_owner}) had its permissions removed."
        ).format(
            owner=self.get_object().owner.username,
            projects=projects,
            previous_owner=previous_owner,
        )
        return mark_safe(msg)


class GroupList(LoginRequiredMixin, ListView):
    paginate_by = 20
    queryset = models.Group.objects.order_by("name")


class GroupDetail(PromgenGuardianPermissionMixin, DetailView):
    permission_required = ["group_admin", "group_member"]
    model = models.Group

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["group_member_form"] = GroupMemberForm(input_object=self.object)
        context["assigned_resources"] = GroupObjectPermission.objects.filter(group=self.object)
        return context


class GroupAddMember(PromgenGuardianPermissionMixin, SingleObjectMixin, View):
    permission_required = ["group_admin"]
    model = models.Group

    def post(self, request, *args, **kwargs):
        group = self.get_object()
        already_members = User.objects.filter(
            Q(username__in=request.POST.getlist("users"))
            & Q(username__in=group.user_set.values_list("username", flat=True))
        )
        new_members = User.objects.filter(username__in=request.POST.getlist("users")).exclude(
            username__in=group.user_set.values_list("username", flat=True)
        )

        if already_members.exists():
            messages.warning(
                request,
                _("Users are already members of Group {group}: {users}").format(
                    group=group.name,
                    users=[user.username for user in already_members],
                ),
            )

        if new_members.exists():
            for user in new_members:
                group.user_set.add(user)
                assign_perm(request.POST["permission"], user, group)
            messages.success(
                request,
                _("Added {users} to Group {group} with permission {permission}").format(
                    users=[user.username for user in new_members],
                    group=group.name,
                    permission=request.POST["permission"],
                ),
            )

        return redirect("group-detail", pk=group.pk)


class GroupUpdateMember(PromgenGuardianPermissionMixin, SingleObjectMixin, View):
    permission_required = ["group_admin"]
    model = models.Group

    def post(self, request, *args, **kwargs):
        group = self.get_object()
        user = User.objects.get_by_natural_key(request.POST["username"])

        if group.user_set.filter(pk=user.pk).exists():
            assign_perm(request.POST["permission"], user, group)
            messages.success(
                request,
                _("Updated permission to {permission} for {user} on Group {group}").format(
                    permission=request.POST["permission"], user=user.username, group=group.name
                ),
            )
        else:
            messages.error(
                request,
                _("User {user} is not a member of Group {group}").format(
                    user=user.username, group=group.name
                ),
            )

        return redirect("group-detail", pk=group.pk)


class GroupRemoveMember(PromgenGuardianPermissionMixin, SingleObjectMixin, View):
    permission_required = ["group_admin"]
    model = models.Group

    def post(self, request, *args, **kwargs):
        group = self.get_object()
        user = User.objects.get_by_natural_key(request.POST["username"])

        if group.user_set.filter(pk=user.pk).exists():
            permissions = get_perms(user, group)
            for perm in permissions:
                remove_perm(perm, user, group)
            group.user_set.remove(user)
            messages.success(
                request,
                _("Removed {user} from Group {group}").format(user=user.username, group=group.name),
            )
        else:
            messages.error(
                request,
                _("User {user} is not a member of Group {group}").format(
                    user=user.username, group=group.name
                ),
            )

        return redirect("group-detail", pk=group.pk)


class GroupRegister(LoginRequiredMixin, CreateView):
    button_label = _("Register Group")
    model = models.Group
    fields = ["name"]

    def form_valid(self, form):
        response = super().form_valid(form)
        group = self.object
        group.user_set.add(self.request.user)
        assign_perm("group_admin", self.request.user, group)
        return response

    def get_success_url(self):
        if self.request.GET.get("next"):
            messages.success(
                self.request,
                _("Group {group} created successfully.").format(group=self.object.name),
            )
            return self.request.GET["next"]
        return super().get_success_url()


class GroupUpdate(PromgenGuardianPermissionMixin, UpdateView):
    permission_required = ["group_admin"]
    button_label = _("Update Group")
    model = models.Group
    fields = ["name"]


class GroupDelete(PromgenGuardianPermissionMixin, DeleteView):
    permission_required = ["group_admin"]
    button_label = _("Delete Group")
    model = models.Group

    def get_success_url(self):
        return reverse("group-list")


class UserMergeView(LoginRequiredMixin, FormView):
    template_name = "promgen/user_merge.html"
    form_class = forms.UserMergeForm

    def form_valid(self, form):
        user_to_merge_into = User.objects.get_by_natural_key(
            form.cleaned_data["user_to_merge_into"]
        )
        user_to_merge_from = User.objects.get_by_natural_key(
            form.cleaned_data["user_to_merge_from"]
        )

        from guardian.models import UserObjectPermission
        from social_django.models import UserSocialAuth

        from promgen.notification.user import NotificationUser

        # Merge social auth accounts
        UserSocialAuth.objects.filter(user=user_to_merge_from).update(user=user_to_merge_into)

        # Update owner fields
        models.Sender.objects.filter(owner=user_to_merge_from).update(owner=user_to_merge_into)
        models.Project.objects.filter(owner=user_to_merge_from).update(owner=user_to_merge_into)
        models.Service.objects.filter(owner=user_to_merge_from).update(owner=user_to_merge_into)

        # Update sender value fields for notification.user type
        models.Sender.objects.filter(
            sender=NotificationUser.__module__, value=str(user_to_merge_from.pk)
        ).update(value=str(user_to_merge_into.pk))

        # Copy group memberships and user permissions
        for group in user_to_merge_from.groups.all():
            user_to_merge_into.groups.add(group)
        for perm in user_to_merge_from.user_permissions.all():
            user_to_merge_into.user_permissions.add(perm)

        # Update object permissions. If both users have different permissions on the same object,
        # we want to keep the highest level of permission to the new user.
        def map_obj_perm_by_perm_rank(user_obj_perms, perm_rank):
            permission_map = {}
            for perm in user_obj_perms:
                obj_id = perm["object_pk"]
                codename = perm["permission__codename"]
                if permission_map.get(obj_id, None):
                    current_rank = perm_rank[permission_map[obj_id]]
                    new_rank = perm_rank[codename]
                    if new_rank > current_rank:
                        permission_map[obj_id] = codename
                else:
                    permission_map[obj_id] = codename
            return permission_map

        user_ids = [user_to_merge_from.id] + [user_to_merge_into.id]

        service_perms = UserObjectPermission.objects.filter(
            user_id__in=user_ids, content_type__app_label="promgen", content_type__model="service"
        ).values("object_pk", "permission__codename")
        service_perm_map = map_obj_perm_by_perm_rank(
            service_perms,
            {"service_admin": 3, "service_editor": 2, "service_viewer": 1},
        )
        for service_id, codename in service_perm_map.items():
            assign_perm(codename, user_to_merge_into, models.Service.objects.get(pk=service_id))

        project_perms = UserObjectPermission.objects.filter(
            user_id__in=user_ids, content_type__app_label="promgen", content_type__model="project"
        ).values("object_pk", "permission__codename")
        project_perm_map = map_obj_perm_by_perm_rank(
            project_perms,
            {"project_admin": 3, "project_editor": 2, "project_viewer": 1},
        )
        for project_id, codename in project_perm_map.items():
            assign_perm(codename, user_to_merge_into, models.Project.objects.get(pk=project_id))

        group_perms = UserObjectPermission.objects.filter(
            user_id__in=user_ids, content_type__app_label="auth", content_type__model="group"
        ).values("object_pk", "permission__codename")
        group_perm_map = map_obj_perm_by_perm_rank(
            group_perms,
            {"group_admin": 2, "group_member": 1},
        )
        for group_id, codename in group_perm_map.items():
            assign_perm(codename, user_to_merge_into, models.Group.objects.get(pk=group_id))

        # Delete the old user, related objects will be cascade deleted
        user_to_merge_from.delete()

        messages.success(
            self.request,
            _("Merged {from_user} into {to_user}.").format(
                from_user=user_to_merge_from.username, to_user=user_to_merge_into.username
            ),
        )
        return redirect("admin:auth_user_changelist")
