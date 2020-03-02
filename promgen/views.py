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
from prometheus_client.core import CounterMetricFamily, GaugeMetricFamily

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, Q
from django.db.utils import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import ugettext as _
from django.views.generic import DetailView, ListView, UpdateView, View
from django.views.generic.base import RedirectView, TemplateView
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.edit import CreateView, DeleteView, FormView

import promgen.templatetags.promgen as macro
from promgen import (
    celery,
    discovery,
    forms,
    mixins,
    models,
    plugins,
    prometheus,
    signals,
    tasks,
    util,
    version,
)
from promgen.shortcuts import resolve_domain

logger = logging.getLogger(__name__)


class ShardList(LoginRequiredMixin, ListView):
    queryset = models.Shard.objects.prefetch_related(
        "project_set__service",
        "project_set__service__owner",
        "project_set__service__notifiers",
        "project_set__service__notifiers__owner",
        "project_set__service__rule_set",
        "project_set",
        "project_set__owner",
        "project_set__farm",
        "project_set__exporter_set",
        "project_set__notifiers",
        "project_set__notifiers__owner",
        "prometheus_set",
    )


class ShardDetail(LoginRequiredMixin, DetailView):
    queryset = models.Shard.objects.prefetch_related(
        "project_set__service",
        "project_set__service__owner",
        "project_set__service__notifiers",
        "project_set__service__notifiers__owner",
        "project_set__service__notifiers__filter_set",
        "project_set__service__rule_set",
        "project_set",
        "project_set__owner",
        "project_set__farm",
        "project_set__exporter_set",
        "project_set__notifiers",
        "project_set__notifiers__owner",
        "project_set__notifiers__filter_set",
    )


class ServiceList(LoginRequiredMixin, ListView):
    paginate_by = 20
    queryset = models.Service.objects.prefetch_related(
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


class HomeList(LoginRequiredMixin, ListView):
    template_name = 'promgen/home.html'

    def get_queryset(self):
        # TODO: Support showing subscribed projects as well
        # Get the list of senders that a user is currently subscribed to
        senders = models.Sender.objects.filter(
            value=self.request.user.username,
            sender='promgen.notification.user',
            content_type=ContentType.objects.get_for_model(models.Service),
        ).values_list('object_id')

        # and return just our list of services
        return models.Service.objects.filter(pk__in=senders).prefetch_related(
            'notifiers',
            'notifiers__owner',
            'owner',
            'rule_set',
            'rule_set__parent',
            'project_set',
            'project_set__farm',
            'project_set__shard',
            'project_set__exporter_set',
            'project_set__notifiers',
            'project_set__owner',
            'project_set__notifiers__owner',
        )


class HostList(LoginRequiredMixin, ListView):
    queryset = models.Host.objects\
        .prefetch_related(
            'farm',
            'farm__project_set',
            'farm__project_set__service',
        )

    def get_context_data(self, **kwargs):
        context = super(HostList, self).get_context_data(**kwargs)
        context['host_groups'] = collections.defaultdict(list)
        for host in context['object_list']:
            context['host_groups'][host.name].append(host)
        context['host_groups'] = dict(context['host_groups'])
        return context


class HostDetail(LoginRequiredMixin, View):
    def get(self, request, slug):
        context = {}
        context['slug'] = self.kwargs['slug']

        context['host_list'] = models.Host.objects\
            .filter(name__icontains=self.kwargs['slug'])\
            .prefetch_related('farm')

        if not context['host_list']:
            return render(request, 'promgen/host_404.html', context, status=404)

        context['farm_list'] = models.Farm.objects.filter(
            id__in=context['host_list'].values_list('farm_id', flat=True)
        )

        context['project_list'] = models.Project.objects.filter(
            id__in=context['farm_list'].values_list('project__id', flat=True)
        ).prefetch_related('notifiers', 'rule_set')

        context['exporter_list'] = models.Exporter.objects.filter(
            project_id__in=context['project_list'].values_list('id', flat=True)
        ).prefetch_related('project', 'project__service')

        context['service_list'] = models.Service.objects.filter(
            id__in=context['project_list'].values_list('service__id', flat=True)
        ).prefetch_related('notifiers', 'rule_set')

        context['rule_list'] = models.Rule.objects.filter(
            Q(id__in=context['project_list'].values_list('rule_set__id')) |
            Q(id__in=context['service_list'].values_list('rule_set__id')) |
            Q(id__in=models.Site.objects.get_current().rule_set.values_list('id'))
        ).select_related('content_type').prefetch_related('content_object')

        context['notifier_list'] = models.Sender.objects.filter(
            Q(id__in=context['project_list'].values_list('notifiers__id')) |
            Q(id__in=context['service_list'].values_list('notifiers__id'))
        ).select_related('content_type').prefetch_related('content_object')

        return render(request, 'promgen/host_detail.html', context)


class AuditList(LoginRequiredMixin, ListView):
    model = models.Audit

    FILTERS = {
        'project': models.Project,
        'service': models.Service,
        'rule': models.Rule,
    }

    def get_queryset(self):
        queryset = self.model.objects\
            .order_by('-created')\
            .prefetch_related(
                'content_object', 'user'
            )

        for key in self.FILTERS:
            if key in self.request.GET:
                obj = self.FILTERS[key].objects.get(pk=self.request.GET[key])
                # Get any log entries for the object itself
                qset = Q(
                    object_id=obj.id,
                    content_type_id=ContentType.objects.get_for_model(obj).id,
                )
                if key in ['project', 'service']:
                    # Look for any registered notifiers
                    qset |= Q(
                        content_type_id=ContentType.objects.get_for_model(models.Sender).id,
                        object_id__in=obj.notifiers.values_list('id', flat=True)
                    )
                    # Look for any registered rules
                    qset |= Q(
                        content_type_id=ContentType.objects.get_for_model(models.Rule).id,
                        object_id__in=obj.rule_set.values_list('id', flat=True)
                    )
                if key == 'project':
                    # Only projects may have exporters
                    qset |= Q(
                        content_type_id=ContentType.objects.get_for_model(models.Exporter).id,
                        object_id__in=obj.exporter_set.values_list('id', flat=True)
                    )
                    # Only projects may have URLs
                    qset |= Q(
                        content_type_id=ContentType.objects.get_for_model(models.URL).id,
                        object_id__in=obj.url_set.values_list('id', flat=True)
                    )
                queryset = queryset.filter(qset)
        if 'user' in self.request.GET:
            queryset = queryset.filter(
                user_id=self.request.GET['user']
            )

        return queryset

    paginate_by = 50


class ServiceDetail(LoginRequiredMixin, DetailView):
    queryset = models.Service.objects\
        .prefetch_related(
            'rule_set',
            'notifiers',
            'notifiers__filter_set',
            'notifiers__owner',
            'project_set',
            'project_set__shard',
            'project_set__farm',
            'project_set__exporter_set',
            'project_set__notifiers',
            'project_set__notifiers__owner'
        )


class ServiceDelete(LoginRequiredMixin, DeleteView):
    model = models.Service

    def get_success_url(self):
        return reverse('service-list')


class ProjectDelete(LoginRequiredMixin, DeleteView):
    model = models.Project

    def get_success_url(self):
        return reverse('service-detail', args=[self.object.service_id])


class NotifierUpdate(LoginRequiredMixin, UpdateView):
    model = models.Sender
    form_class = forms.NotifierUpdate

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()
        # For populating breadcrumb
        context[obj.content_type.model] = obj.content_object
        return context

    def post(self, request, pk):
        if 'filter.pk' in request.POST:
            f = models.Filter.objects.get(pk=request.POST['filter.pk'])
            f.delete()
            messages.success(request, 'Removed filter {f.name} {f.value}'.format(f=f))
        if 'filter.name' in request.POST:
            obj = self.get_object()
            f, created = obj.filter_set.get_or_create(name=request.POST['filter.name'], value=request.POST['filter.value'])
            if created:
                messages.success(request, 'Created filter {f.name} {f.value}'.format(f=f))
            else:
                messages.warning(request, 'Updated filter {f.name} {f.value}'.format(f=f))
        if 'next' in request.POST:
            return redirect(request.POST['next'])
        return self.get(self, request, pk)


class NotifierDelete(LoginRequiredMixin, DeleteView):
    model = models.Sender

    def get_success_url(self):
        if 'next' in self.request.POST:
            return self.request.POST['next']
        if hasattr(self.object.content_object, 'get_absolute_url'):
            return self.object.content_object.get_absolute_url()
        return reverse("profile")


class NotifierTest(LoginRequiredMixin, View):
    def post(self, request, pk):
        sender = get_object_or_404(models.Sender, id=pk)
        try:
            sender.test()
        except Exception:
            messages.warning(request, 'Error sending test message with ' + sender.sender)
        else:
            messages.info(request, 'Sent test message with ' + sender.sender)

        if 'next' in request.POST:
            return redirect(request.POST['next'])
        if hasattr(sender.content_object, 'get_absolute_url'):
            return redirect(sender.content_object)
        return redirect("profile")


class ExporterDelete(LoginRequiredMixin, DeleteView):
    model = models.Exporter

    def get_success_url(self):
        return reverse('project-detail', args=[self.object.project_id])


class ExporterToggle(LoginRequiredMixin, View):
    def post(self, request, pk):
        exporter = get_object_or_404(models.Exporter, id=pk)
        exporter.enabled = not exporter.enabled
        exporter.save()
        signals.trigger_write_config.send(request)
        return JsonResponse({'redirect': exporter.project.get_absolute_url()})


class RuleDelete(mixins.PromgenPermissionMixin, DeleteView):
    model = models.Rule

    def get_permission_denied_message(self):
        return 'Unable to delete rule %s. User lacks permission' % self.object

    def get_permission_required(self):
        # In the case of rules, we want to make sure the user has permission
        # to delete the rule itself, but also permission to change the linked object
        self.object = self.get_object()
        obj = self.object._meta
        tgt = self.object.content_object._meta

        yield '{}.delete_{}'.format(obj.app_label, obj.model_name)
        yield '{}.change_{}'.format(tgt.app_label, tgt.model_name)

    def get_success_url(self):
        return self.object.content_object.get_absolute_url()


class RuleToggle(mixins.PromgenPermissionMixin, SingleObjectMixin, View):
    model = models.Rule

    def get_permission_denied_message(self):
        return 'Unable to toggle rule %s. User lacks permission' % self.object

    def get_permission_required(self):
        # In the case of rules, we want to make sure the user has permission
        # to delete the rule itself, but also permission to change the linked object
        self.object = self.get_object()
        obj = self.object._meta
        tgt = self.object.content_object._meta

        yield '{}.change_{}'.format(obj.app_label, obj.model_name)
        yield '{}.change_{}'.format(tgt.app_label, tgt.model_name)

    def post(self, request, pk):
        self.object.enabled = not self.object.enabled
        self.object.save()
        return JsonResponse({'redirect': self.object.content_object.get_absolute_url()})


class HostDelete(LoginRequiredMixin, DeleteView):
    model = models.Host

    def get_success_url(self):
        # If there's only one linked project then we redirect to the project page
        # otherwise we redirect to our farm page
        if self.object.farm.project_set.count():
            return self.object.farm.project_set.first().get_absolute_url()
        return self.object.farm.get_absolute_url()


class ProjectDetail(LoginRequiredMixin, DetailView):
    queryset = models.Project.objects.prefetch_related(
        'rule_set',
        'rule_set__parent',
        'notifiers',
        'notifiers__owner',
        'shard',
        'service',
        'service__rule_set',
        'service__rule_set__parent',
    )

    def get_context_data(self, **kwargs):
        context = super(ProjectDetail, self).get_context_data(**kwargs)
        context['sources'] = models.Farm.driver_set()
        context['url_form'] = forms.URLForm()
        return context


class FarmList(LoginRequiredMixin, ListView):
    paginate_by = 50
    queryset = models.Farm.objects\
        .prefetch_related(
            'project_set',
            'host_set',
        )


class FarmDetail(LoginRequiredMixin, DetailView):
    model = models.Farm


class FarmUpdate(LoginRequiredMixin, UpdateView):
    model = models.Farm
    button_label = _('Update Farm')
    template_name = 'promgen/farm_form.html'
    form_class = forms.FarmForm

    def get_context_data(self, **kwargs):
        context = super(FarmUpdate, self).get_context_data(**kwargs)
        context['project'] = self.object.project_set.first()
        context['service'] = context['project'].service
        return context

    def form_valid(self, form):
        farm, created = models.Farm.objects.update_or_create(
            id=self.kwargs['pk'],
            defaults=form.clean(),
        )
        return HttpResponseRedirect(reverse('project-detail', args=[farm.project_set.first().id]))


class FarmDelete(LoginRequiredMixin, RedirectView):
    pattern_name = 'farm-detail'

    def post(self, request, pk):
        farm = get_object_or_404(models.Farm, id=pk)
        farm.delete()

        return HttpResponseRedirect(
            request.POST.get('next', reverse('service-list'))
        )


class UnlinkFarm(LoginRequiredMixin, View):
    def post(self, request, pk):
        project = get_object_or_404(models.Project, id=pk)
        oldfarm, project.farm = project.farm, None
        project.save()
        signals.trigger_write_config.send(request)

        if oldfarm.project_set.count() == 0 and oldfarm.editable is False:
            logger.debug('Cleaning up old farm %s', oldfarm)
            oldfarm.delete()

        return HttpResponseRedirect(reverse('project-detail', args=[project.id]))


class RulesList(LoginRequiredMixin, ListView, mixins.ServiceMixin):
    template_name = "promgen/rule_list.html"
    queryset = models.Rule.objects.prefetch_related("content_type", "content_object")

    def get_context_data(self, **kwargs):
        context = super(RulesList, self).get_context_data(**kwargs)

        site_rules = models.Rule.objects.filter(
            content_type__model="site", content_type__app_label="promgen"
        ).prefetch_related(
            "content_object",
            "rulelabel_set",
            "ruleannotation_set",
        )

        service_rules = models.Rule.objects.filter(
            content_type__model="service", content_type__app_label="promgen"
        ).prefetch_related(
            "content_object",
            "content_object",
            "rulelabel_set",
            "ruleannotation_set",
            "parent",
        )

        project_rules = models.Rule.objects.filter(
            content_type__model="project", content_type__app_label="promgen"
        ).prefetch_related(
            "content_object",
            "content_object__service",
            "content_object__service",
            "rulelabel_set",
            "ruleannotation_set",
            "parent",
        )

        context["rule_list"] = chain(site_rules, service_rules, project_rules)

        return context


class RulesCopy(LoginRequiredMixin, View):
    def post(self, request, pk):
        original = get_object_or_404(models.Rule, id=pk)
        form = forms.RuleCopyForm(request.POST)

        if form.is_valid():
            rule = original.copy_to(**form.clean())
            return HttpResponseRedirect(reverse('rule-edit', args=[rule.id]))
        else:
            return HttpResponseRedirect(reverse('service-detail', args=[pk]))


class FarmRefresh(LoginRequiredMixin, RedirectView):
    pattern_name = 'farm-detail'

    def post(self, request, pk):
        farm = get_object_or_404(models.Farm, id=pk)
        # If any hosts are added or removed, then we want to
        # trigger a config refresh
        if any(farm.refresh()):
            signals.trigger_write_config.send(request)
        messages.info(request, 'Refreshed hosts')
        if 'next' in request.POST:
            return HttpResponseRedirect(request.POST['next'])
        # If we don't have an explicit redirect, we can redirect to the farm
        # itself
        return redirect(farm)


class FarmConvert(LoginRequiredMixin, RedirectView):
    pattern_name = 'farm-detail'

    def post(self, request, pk):
        farm = get_object_or_404(models.Farm, id=pk)
        farm.source = discovery.FARM_DEFAULT

        try:
            farm.save()
        except IntegrityError:
            return render(request, 'promgen/farm_duplicate.html', {
                'pk': farm.pk,
                'next': request.POST.get('next', reverse('farm-detail', args=[farm.pk])),
                'farm_list': models.Farm.objects.filter(name=farm.name)
            })

        return HttpResponseRedirect(
            request.POST.get('next', reverse('farm-detail', args=[farm.pk]))
        )


class FarmLink(LoginRequiredMixin, View):
    def get(self, request, pk, source):
        context = {
            'source': source,
            'project': get_object_or_404(models.Project, id=pk),
            'farm_list': sorted(models.Farm.fetch(source=source)),
        }
        return render(request, 'promgen/link_farm.html', context)

    def post(self, request, pk, source):
        project = get_object_or_404(models.Project, id=pk)
        farm, created = models.Farm.objects.get_or_create(
            name=request.POST['farm'],
            source=source,
        )
        if created:
            logger.info('Importing %s from %s', farm.name, source)
            farm.refresh()
            messages.info(request, 'Refreshed hosts')
        project.farm = farm
        project.save()
        return HttpResponseRedirect(reverse('project-detail', args=[project.id]))


class ExporterRegister(LoginRequiredMixin, FormView, mixins.ProjectMixin):
    model = models.Exporter
    template_name = 'promgen/exporter_form.html'
    form_class = forms.ExporterForm

    def form_valid(self, form):
        project = get_object_or_404(models.Project, id=self.kwargs['pk'])
        exporter, _ = models.Exporter.objects.get_or_create(project=project, **form.clean())
        return HttpResponseRedirect(reverse('project-detail', args=[project.id]))

class ExporterScrape(LoginRequiredMixin, FormView):
    # TODO: Move to /rest/project/<slug>/scrape
    form_class = forms.ExporterForm

    def form_invalid(self, form):
        return JsonResponse(
            {"message": "Form Errors", "errors": form.errors}, status=400
        )

    def form_valid(self, form):
        futures = []
        farm = get_object_or_404(models.Farm, id=self.kwargs["pk"])

        # The default __metrics_path__ for Prometheus is /metrics so we need to
        # manually add it here in the case it's not set for our test
        if not form.cleaned_data["path"]:
            form.cleaned_data["path"] = "/metrics"

        def query():
            with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                for host in farm.host_set.all():
                    futures.append(
                        executor.submit(
                            util.get,
                            "{scheme}://{host}:{port}{path}".format(
                                host=host.name, **form.cleaned_data
                            ),
                        )
                    )
                for future in concurrent.futures.as_completed(futures):
                    try:
                        result = future.result()
                        result.raise_for_status()
                        yield result.url, result.status_code
                    except requests.ConnectionError as e:
                        logger.warning("Error connecting to server")
                        yield e.request.url, "Error connecting to server"
                    except requests.RequestException as e:
                        logger.warning("Error with response")
                        yield e.request.url, str(e)
                    except Exception:
                        logger.exception("Unknown Exception")
                        yield "Unknown URL", "Unknown error"

        return JsonResponse(dict(query()))


class URLRegister(LoginRequiredMixin, FormView, mixins.ProjectMixin):
    model = models.URL
    template_name = 'promgen/url_form.html'
    form_class = forms.URLForm

    def form_valid(self, form):
        project = get_object_or_404(models.Project, id=self.kwargs['pk'])
        url, _ = models.URL.objects.get_or_create(project=project, **form.clean())
        return HttpResponseRedirect(reverse('project-detail', args=[project.id]))


class URLDelete(LoginRequiredMixin, DeleteView):
    model = models.URL

    def get_success_url(self):
        return reverse('project-detail', args=[self.object.project_id])


class URLList(LoginRequiredMixin, ListView):
    queryset = models.URL.objects\
        .prefetch_related(
            'project',
            'project__service',
            'project__shard',
            'probe',
        )


class ProjectRegister(LoginRequiredMixin, CreateView):
    button_label = _("Project Register")
    model = models.Project
    fields = ["name", "description", "owner", "shard"]

    def get_initial(self):
        initial = {"owner": self.request.user}
        if "shard" in self.request.GET:
            initial["shard"] = get_object_or_404(
                models.Shard, pk=self.request.GET["shard"]
            )
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["service"] = get_object_or_404(models.Service, id=self.kwargs["pk"])
        context["shard_list"] = models.Shard.objects.all()
        return context

    def form_valid(self, form):
        form.instance.service_id = self.kwargs["pk"]
        return super().form_valid(form)


class ProjectUpdate(LoginRequiredMixin, UpdateView):
    model = models.Project
    button_label = _("Project Update")
    template_name = "promgen/project_form.html"
    fields = ["name", "description", "owner", "service", "shard"]

    def get_context_data(self, **kwargs):
        context = super(ProjectUpdate, self).get_context_data(**kwargs)
        context["service"] = self.object.service
        context["shard_list"] = models.Shard.objects.all()
        return context


class ServiceUpdate(LoginRequiredMixin, UpdateView):
    button_label = _('Update Service')
    form_class = forms.ServiceUpdate
    model = models.Service


class RuleDetail(LoginRequiredMixin, DetailView):
    queryset = models.Rule.objects.prefetch_related(
        "content_object",
        "content_type",
        "ruleannotation_set",
        "rulelabel_set",
        'overrides',
        'overrides__ruleannotation_set',
        'overrides__rulelabel_set',
        "overrides__content_object",
        "overrides__content_type",
    )


class RuleUpdate(mixins.PromgenPermissionMixin, UpdateView):
    def get_permission_denied_message(self):
        return "Unable to edit rule %s. User lacks permission" % self.object

    def get_permission_required(self):
        # In the case of rules, we want to make sure the user has permission
        # to change the rule itself, but also permission to change the linked object
        self.object = self.get_object()
        obj = self.object._meta
        tgt = self.object.content_object._meta

        yield "{}.change_{}".format(obj.app_label, obj.model_name)
        yield "{}.change_{}".format(tgt.app_label, tgt.model_name)

    queryset = models.Rule.objects.prefetch_related(
        "content_object", "overrides", "overrides__content_object"
    )
    template_name = "promgen/rule_update.html"
    form_class = forms.AlertRuleForm

    def get_context_data(self, **kwargs):
        context = super(RuleUpdate, self).get_context_data(**kwargs)
        context.setdefault("formset_labels", forms.LabelFormset(instance=self.object))
        context.setdefault("formset_annotations", forms.AnnotationFormset(instance=self.object))
        context["macro"] = macro.EXCLUSION_MACRO
        context["rules"] = [self.object.parent] if self.object.parent else [self.object]
        return context

    def form_invalid(self, **kwargs):
        """If the form is invalid, render the invalid form."""
        return self.render_to_response(self.get_context_data(**kwargs))

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        # Save a copy of our forms into a context var that we can use
        # to re-render our form properly in case of errors
        context = {}
        context["form"] = form = self.get_form()
        context["formset_labels"] = form_labels = forms.LabelFormset(
            request.POST, request.FILES, instance=self.object
        )
        context["formset_annotations"] = form_annotations = forms.AnnotationFormset(
            request.POST, request.FILES, instance=self.object
        )

        # Check validity of our labels and annotations in Django before we try to render
        if not all([form_labels.is_valid(), form_annotations.is_valid()]):
            return self.form_invalid(**context)

        # Populate our cached_properties so we can render a test
        # populate only rows with a 'value' so that we skip fields we're deleting
        # see Django docs on cached_property and promgen.forms.RuleForm.clean()
        form.instance.labels = {
            l["name"]: l["value"] for l in form_labels.cleaned_data if "value" in l
        }
        form.instance.annotations = {
            a["name"]: a["value"] for a in form_annotations.cleaned_data if "value" in a
        }

        # With our labels+annotations manually cached we can test
        if not form.is_valid():
            return self.form_invalid(**context)

        # Save our labels
        for instance in form_labels.save():
            messages.info(request, "Added {} to {}".format(instance.name, self.object))

        # Save our annotations
        for instance in form_annotations.save():
            messages.info(request, "Added {} to {}".format(instance.name, self.object))

        return self.form_valid(form)


class AlertRuleRegister(mixins.PromgenPermissionMixin, mixins.RuleFormMixin, FormView):
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
        context["rule"].set_object(
            self.kwargs["content_type"], self.kwargs["object_id"]
        )
        context["macro"] = macro.EXCLUSION_MACRO
        return context

    def form_valid(self, form):
        form.instance.save()
        form.instance.add_label(
            form.instance.content_type.model, form.instance.content_object.name
        )
        return HttpResponseRedirect(form.instance.get_absolute_url())

    def form_import(self, form, content_object):
        data = form.clean()
        counters = prometheus.import_rules_v2(data["rules"], content_object)
        messages.info(self.request, "Imported %s" % counters)
        return HttpResponseRedirect(content_object.get_absolute_url())


class ServiceRegister(LoginRequiredMixin, CreateView):
    button_label = _("Register Service")
    model = models.Service
    fields = ["name", "description", "owner"]

    def get_initial(self):
        return {"owner": self.request.user}


class FarmRegister(LoginRequiredMixin, FormView, mixins.ProjectMixin):
    model = models.Farm
    button_label = _('Register Farm')
    template_name = 'promgen/farm_form.html'
    form_class = forms.FarmForm

    def form_valid(self, form):
        project = get_object_or_404(models.Project, id=self.kwargs['pk'])
        farm, _ = models.Farm.objects.get_or_create(source=discovery.FARM_DEFAULT, **form.clean())
        project.farm = farm
        project.save()
        return HttpResponseRedirect(project.get_absolute_url())


class ProjectNotifierRegister(LoginRequiredMixin, FormView, mixins.ProjectMixin):
    model = models.Sender
    template_name = 'promgen/notifier_form.html'
    form_class = forms.SenderForm

    def form_valid(self, form):
        project = get_object_or_404(models.Project, id=self.kwargs['pk'])
        sender, created = models.Sender.objects.get_or_create(obj=project, owner=self.request.user, **form.clean())
        signals.check_user_subscription(models.Sender, sender, created, self.request)
        return HttpResponseRedirect(project.get_absolute_url())


class ServiceNotifierRegister(LoginRequiredMixin, FormView, mixins.ServiceMixin):
    model = models.Sender
    template_name = 'promgen/notifier_form.html'
    form_class = forms.SenderForm

    def form_valid(self, form):
        service = get_object_or_404(models.Service, id=self.kwargs['pk'])
        sender, created = models.Sender.objects.get_or_create(obj=service, owner=self.request.user, **form.clean())
        signals.check_user_subscription(models.Sender, sender, created, self.request)
        return HttpResponseRedirect(service.get_absolute_url())


class SiteDetail(LoginRequiredMixin, TemplateView):
    template_name = "promgen/site_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["rule_list"] = models.Rule.objects.filter(
            content_type__model="site", content_type__app_label="promgen"
        ).prefetch_related("content_object", "rulelabel_set", "ruleannotation_set")
        return context


class Profile(LoginRequiredMixin, FormView):
    form_class = forms.SenderForm
    model = models.Sender
    template_name = "promgen/profile.html"

    def get_context_data(self, **kwargs):
        context = super(Profile, self).get_context_data(**kwargs)
        context['discovery_plugins'] = [entry for entry in plugins.discovery()]
        context['notifier_plugins'] = [entry for entry in plugins.notifications()]
        context['notifiers'] = {'notifiers': models.Sender.objects.filter(obj=self.request.user)}
        context['subscriptions'] = models.Sender.objects.filter(
            sender='promgen.notification.user', value=self.request.user.username)
        return context

    def form_valid(self, form):
        sender, _ = models.Sender.objects.get_or_create(obj=self.request.user, owner=self.request.user, **form.clean())
        return redirect('status')


class HostRegister(LoginRequiredMixin, FormView):
    model = models.Host
    template_name = "promgen/host_form.html"
    form_class = forms.HostForm

    def get_context_data(self, **kwargs):
        context = super(HostRegister, self).get_context_data(**kwargs)
        context["farm"] = get_object_or_404(models.Farm, pk=self.kwargs["pk"])
        context["project"] = context["farm"].project_set.first()
        return context

    def form_valid(self, form):
        farm = get_object_or_404(models.Farm, id=self.kwargs["pk"])
        for hostname in form.cleaned_data["hosts"]:
            host, created = models.Host.objects.get_or_create(
                name=hostname, farm_id=farm.id
            )
            if created:
                logger.debug("Added %s to %s", host.name, farm.name)

        if farm.project_set.count() == 0:
            return redirect("farm-detail", pk=farm.id)
        return redirect("project-detail", pk=farm.project_set.first().id)


class ApiConfig(View):
    def get(self, request):
        return HttpResponse(prometheus.render_config(), content_type='application/json')

    def post(self, request, *args, **kwargs):
        try:
            body = json.loads(request.body.decode('utf-8'))

            prometheus.import_config(body, **kwargs)
        except Exception as e:
            return HttpResponse(e, status=400)

        return HttpResponse('Success', status=202)


class ApiQueue(View):
    def post(self, request):
        signals.trigger_write_config.send(request)
        signals.trigger_write_rules.send(request)
        signals.trigger_write_urls.send(request)
        return HttpResponse('OK', status=202)


class Commit(LoginRequiredMixin, View):
    def post(self, request):
        signals.trigger_write_config.send(request)
        return HttpResponseRedirect(request.POST.get('next', '/'))


class _ExportRules(View):
    def format(self, rules=None, name='promgen'):
        content = prometheus.render_rules(rules)
        response = HttpResponse(content)
        response['Content-Type'] = 'application/x-yaml'
        response['Content-Disposition'] = 'attachment; filename=%s.rule.yml' % name
        return response


class RulesConfig(_ExportRules):
    def get(self, request):
        return self.format()


class RuleExport(_ExportRules):
    def get(self, request, content_type, object_id):
        ct = ContentType.objects.get(app_label="promgen", model=content_type).get_object_for_this_type(pk=object_id)
        rules = models.Rule.objects.filter(obj=ct)
        return self.format(rules)


class URLConfig(View):
    def get(self, request):
        return HttpResponse(prometheus.render_urls(), content_type='application/json')

    def post(self, request):
        tasks.write_urls()
        return HttpResponse('OK', status=202)


class Alert(View):
    def post(self, request, *args, **kwargs):
        # Normally it would be more 'correct' to check our 'alert_blacklist' here and avoid
        # writing to the database, but to keep the alert ingestion queue as simple as possible
        # we will go ahead and write all alerts to the database and then filter out (delete)
        # when we run tasks.process_alert
        alert = models.Alert.objects.create(body=request.body.decode("utf-8"))
        tasks.process_alert.delay(alert.pk)
        return HttpResponse("OK", status=202)


class AlertList(LoginRequiredMixin, ListView):
    paginate_by = 20
    queryset = models.Alert.objects.order_by("-created")

    def get_queryset(self):
        search = self.request.GET.get('search')
        if search:
            return self.queryset.filter(
                Q(alertlabel__name="Service", alertlabel__value__icontains=search)
                | Q(alertlabel__name="Project", alertlabel__value__icontains=search)
                | Q(alertlabel__name="Job", alertlabel__value__icontains=search)
            )

        qs = self.queryset
        for key, value in self.request.GET.items():
            if key in ["page", "search"]:
                continue
            qs = qs.filter(alertlabel__name=key, alertlabel__value=value)
        return qs

class AlertDetail(LoginRequiredMixin, DetailView):
    model = models.Alert


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
        v.add_metric([version.__version__, platform.python_version()], 1)
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


        yield GaugeMetricFamily(
            "promgen_shards", "Registered Shards", models.Shard.objects.count()
        )
        yield GaugeMetricFamily(
            "promgen_exporters", "Registered Exporters", models.Exporter.objects.count()
        )
        yield GaugeMetricFamily(
            "promgen_services", "Registered Services", models.Service.objects.count()
        )
        yield GaugeMetricFamily(
            "promgen_projects", "Registered Projects", models.Project.objects.count()
        )
        yield GaugeMetricFamily(
            "promgen_rules", "Registered Rules", models.Rule.objects.count()
        )
        yield GaugeMetricFamily(
            "promgen_urls", "Registered URLs", models.URL.objects.count()
        )

        # TODO Properly de-duplicate after refactoring
        yield GaugeMetricFamily(
            "promgen_hosts",
            "Registered Hosts",
            len(models.Host.objects.values("name").annotate(Count("name"))),
        )

        notifier = GaugeMetricFamily(
            "promgen_notifiers", "Registered Notifiers", labels=["type", "sender"]
        )
        for entry in models.Sender.objects.values(
            "content_type__model", "sender"
        ).annotate(Count("sender"), count=Count("content_type")):
            notifier.add_metric(
                [entry["content_type__model"], entry["sender"]], entry["count"]
            )

        yield notifier


class Search(LoginRequiredMixin, View):
    def get(self, request):
        MAPPING = {
            'farm_list': {
                'field': ('name__icontains',),
                'model': models.Farm,
                'prefetch': ('project_set', 'host_set'),
                'query': ('search', 'var-farm'),
            },
            'host_list': {
                'field': ('name__icontains',),
                'model': models.Host,
                'query': ('search', 'var-instance'),
            },
            'project_list': {
                'field': ('name__icontains',),
                'model': models.Project,
                'prefetch': ('service', 'notifiers', 'exporter_set', 'notifiers__owner'),
                'query': ('search', 'var-project'),
            },
            'rule_list': {
                'field': ('name__icontains', 'clause__icontains'),
                'model': models.Rule,
                'prefetch': ('content_object', 'ruleannotation_set', 'rulelabel_set'),
                'query': ('search', ),
            },
            'service_list': {
                'field': ('name__icontains',),
                'model': models.Service,
                'prefetch': ('project_set', 'rule_set', 'notifiers', 'notifiers__owner'),
                'query': ('search', 'var-service'),
            }
        }

        context = {}
        for target, obj in MAPPING.items():
            # If our potential search keys are not in our query string
            # then we can bail out quickly
            query = set(obj['query']).intersection(request.GET.keys())
            if not query:
                logger.info('query for %s: <skipping>', target)
                continue
            logger.info('query for %s: %s', target, query)

            qs = obj['model'].objects
            if 'prefetch' in obj:
                qs = qs.prefetch_related(*obj['prefetch'])

            # Build our OR query by combining Q lookups
            filters = None
            for var in query:
                for field in obj['field']:
                    if filters:
                        filters |= Q(**{field: request.GET[var]})
                    else:
                        filters = Q(**{field: request.GET[var]})
            logger.info('filtering %s by %s', target, filters)

            qs = qs.filter(filters)
            context[target] = qs

        return render(request, 'promgen/search.html', context)


class RuleImport(mixins.PromgenPermissionMixin, FormView):
    form_class = forms.ImportRuleForm
    template_name = 'promgen/rule_import.html'

    # Since rule imports can change a lot of site wide stuff we
    # require site edit permission here
    permission_required = ('promgen.change_site', 'promgen.change_rule')
    permisison_denied_message = 'User lacks permission to import'

    def form_valid(self, form):
        data = form.clean()
        if data.get('file_field'):
            rules = data['file_field'].read().decode('utf8')
        elif data.get('rules'):
            rules = data.get('rules')
        else:
            messages.warning(self.request, 'Missing rules')
            return self.form_invalid(form)

        try:
            counters = prometheus.import_rules_v2(rules)
            messages.info(self.request, 'Imported %s' % counters)
            return redirect('rule-import')
        except:
            messages.error(self.request, 'Error importing rules')
            return self.form_invalid(form)


class Import(mixins.PromgenPermissionMixin, FormView):
    template_name = 'promgen/import_form.html'
    form_class = forms.ImportConfigForm

    # Since imports can change a lot of site wide stuff we
    # require site edit permission here
    permission_required = (
        'promgen.change_site', 'promgen.change_rule', 'promgen.change_exporter'
    )

    permission_denied_message = 'User lacks permission to import'

    def form_valid(self, form):
        data = form.clean()
        if data.get('file_field'):
            messages.info(self.request, 'Importing config from file')
            config = data['file_field'].read().decode('utf8')
        elif data.get('url'):
            messages.info(self.request, 'Importing config from url')
            response = util.get(data['url'])
            response.raise_for_status()
            config = response.text
        elif data.get('config'):
            messages.info(self.request, 'Importing config')
            config = data['config']
        else:
            messages.warning(self.request, 'Missing config')
            return self.form_invalid(form)

        kwargs = {}
        # This also lets us catch passing an empty string to signal using
        # the shard value from the post request
        if data.get('shard'):
            kwargs['replace_shard'] = data.get('shard')

        imported, skipped = prometheus.import_config(json.loads(config), **kwargs)

        if imported:
            counters = {key: len(imported[key]) for key in imported}
            messages.info(self.request, 'Imported %s' % counters)

        if skipped:
            counters = {key: len(skipped[key]) for key in skipped}
            messages.info(self.request, 'Skipped %s' % counters)

        # If we only have a single object in a category, automatically
        # redirect to that category to make things easier to understand
        if len(imported['Project']) == 1:
            return HttpResponseRedirect(imported['Project'][0].get_absolute_url())
        if len(imported['Service']) == 1:
            return HttpResponseRedirect(imported['Service'][0].get_absolute_url())
        if len(imported['Shard']) == 1:
            return HttpResponseRedirect(imported['Shard'][0].get_absolute_url())

        return redirect('service-list')


class RuleTest(LoginRequiredMixin, View):
    def post(self, request, pk):
        if pk == 0:
            rule = models.Rule()
            rule.set_object(request.POST['content_type'], request.POST['object_id'])
        else:
            rule = get_object_or_404(models.Rule, id=pk)

        query = macro.rulemacro(rule, request.POST['query'])
        # Since our rules affect all servers we use Promgen's proxy-query to test our rule
        # against all the servers at once
        url = resolve_domain('proxy-query')

        logger.debug('Querying %s with %s', url, query)
        start = time.time()
        result = util.get(url, {'query': query}).json()
        duration = datetime.timedelta(seconds=(time.time() - start))

        context = {'status': result['status'], 'duration': duration, 'query': query}
        context['data'] = result.get('data', {})

        context['errors'] = {}

        metrics = context['data'].get('result', [])
        if metrics:
            context['collapse'] = len(metrics) > 5
            for row in metrics:
                if 'service' not in row['metric'] and \
                        'project' not in row['metric']:
                    context['errors']['routing'] = 'Some metrics are missing service and project labels so Promgen will be unable to route message'
                    context['status'] = 'warning'
        else:
            context['status'] = 'info'
            context['errors']['no_results'] = 'No Results. May need to remove conditional check (> < ==) to verity'

        # Place this at the bottom to have a query error show up as danger
        if result['status'] != 'success':
            context['status'] = 'danger'
            context['errors']['Query'] = result['error']

        return JsonResponse({request.POST['target']: render_to_string('promgen/ajax_clause_check.html', context)})
