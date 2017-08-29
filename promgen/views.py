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
from urllib.parse import urljoin

import requests
from dateutil import parser
from django import forms as django_forms
from django.conf import settings
from django.contrib import messages
from django.db.models import Count, Q, prefetch_related_objects
from django.db.utils import IntegrityError
from django.forms import inlineformset_factory
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils.text import slugify
from django.utils.translation import ugettext as _
from django.views.generic import DetailView, ListView, UpdateView, View
from django.views.generic.base import ContextMixin, RedirectView
from django.views.generic.edit import DeleteView, FormView
from prometheus_client import Gauge, generate_latest

import promgen.templatetags.promgen as macro
from promgen import (celery, forms, models, plugins, prometheus, signals, util,
                     version, discovery)

logger = logging.getLogger(__name__)


class ProjectMixin(ContextMixin):
    def get_context_data(self, **kwargs):
        context = super(ProjectMixin, self).get_context_data(**kwargs)
        if 'pk' in self.kwargs:
            context['project'] = get_object_or_404(models.Project, id=self.kwargs['pk'])
        return context


class ServiceMixin(ContextMixin):
    def get_context_data(self, **kwargs):
        context = super(ServiceMixin, self).get_context_data(**kwargs)
        if 'pk' in self.kwargs:
            context['service'] = get_object_or_404(models.Service, id=self.kwargs['pk'])
        return context


class GlobalRulesMixin(object):
    def get_context_data(self, **kwargs):
        context = super(GlobalRulesMixin, self).get_context_data(**kwargs)
        context['global_rule_set'] = models.Service.default().rule_set
        return context


class ShardList(ListView):
    queryset = models.Shard.objects\
        .prefetch_related(
            'prometheus_set',
            'service_set',
            'service_set__notifiers',
            'service_set__project_set',
            'service_set__project_set__farm',
            'service_set__project_set__exporter_set',
            'service_set__project_set__notifiers')


class ShardDetail(DetailView):
    queryset = models.Shard.objects\
        .prefetch_related(
            'service_set',
            'service_set__notifiers',
            'service_set__rule_set',
            'service_set__project_set',
            'service_set__project_set__farm',
            'service_set__project_set__exporter_set',
            'service_set__project_set__notifiers')


class ServiceList(ListView):
    queryset = models.Service.objects\
        .prefetch_related(
            'notifiers',
            'rule_set',
            'rule_set__parent',
            'project_set',
            'project_set__farm',
            'project_set__exporter_set',
            'project_set__notifiers'
        )


class HostList(ListView):
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


class HostDetail(View):
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

        context['service_list'] = models.Service.objects.filter(
            id__in=context['project_list'].values_list('service__id', flat=True)
        ).prefetch_related('notifiers', 'rule_set')

        context['rule_list'] = models.Rule.objects.filter(
            Q(id__in=context['project_list'].values_list('rule_set__id')) |
            Q(id__in=context['service_list'].values_list('rule_set__id')) |
            Q(id__in=models.Service.default().rule_set.values_list('id'))
        ).select_related('content_type').prefetch_related('content_object')

        context['notifier_list'] = models.Sender.objects.filter(
            Q(id__in=context['project_list'].values_list('notifiers__id')) |
            Q(id__in=context['service_list'].values_list('notifiers__id'))
        ).select_related('content_type').prefetch_related('content_object')

        return render(request, 'promgen/host_detail.html', context)


class AuditList(ListView):
    queryset = models.Audit.objects\
        .order_by('-created')\
        .prefetch_related(
            'content_object',
        )

    paginate_by = 50


class ServiceDetail(GlobalRulesMixin, DetailView):
    queryset = models.Service.objects\
        .prefetch_related(
            'rule_set',
            'notifiers',
            'project_set',
            'project_set__farm',
            'project_set__exporter_set',
            'project_set__notifiers')


class ServiceDelete(DeleteView):
    model = models.Service

    def get_success_url(self):
        return reverse('shard-detail', args=[self.object.shard_id])


class ProjectDelete(DeleteView):
    model = models.Project

    def get_success_url(self):
        return reverse('service-detail', args=[self.object.service_id])


class NotifierDelete(DeleteView):
    model = models.Sender

    def get_success_url(self):
        return self.object.content_object.get_absolute_url()


class NotifierTest(View):
    def post(self, request, pk):
        sender = get_object_or_404(models.Sender, id=pk)
        for entry in plugins.notifications():
            if entry.module_name == sender.sender:
                try:
                    entry.load()().test(sender.value, {
                        'generatorURL': 'Promgen',
                        'status': 'Test',
                        'labels': {},
                        'annotations': {
                            'alertname': 'Test Alert',
                        },
                    })
                except:
                    logger.exception('Error sending test message with %s', entry.module_name)
                    messages.warning(request, 'Error sending test message with ' + entry.module_name)
                else:
                    messages.info(request, 'Sent test message with ' + entry.module_name)

        return HttpResponseRedirect(sender.content_object.get_absolute_url())


class ExporterDelete(DeleteView):
    model = models.Exporter

    def get_success_url(self):
        return reverse('project-detail', args=[self.object.project_id])


class ExporterToggle(View):
    def post(self, request, pk):
        exporter = get_object_or_404(models.Exporter, id=pk)
        exporter.enabled = not exporter.enabled
        exporter.save()
        signals.trigger_write_config.send(request)
        return JsonResponse({'redirect': exporter.project.get_absolute_url()})


class RuleDelete(DeleteView):
    model = models.Rule

    def get_success_url(self):
        return self.object.content_object.get_absolute_url()


class RuleToggle(View):
    def post(self, request, pk):
        rule = get_object_or_404(models.Rule, id=pk)
        rule.enabled = not rule.enabled
        rule.save()
        return JsonResponse({'redirect': rule.content_object.get_absolute_url()})


class HostDelete(DeleteView):
    model = models.Host

    def get_success_url(self):
        # If there's only one linked project then we redirect to the project page
        # otherwise we redirect to our farm page
        if self.object.farm.project_set.count():
            return self.object.farm.project_set.first().get_absolute_url()
        return self.object.farm.get_absolute_url()


class ProjectDetail(DetailView):
    queryset = models.Project.objects.prefetch_related(
        'rule_set',
        'rule_set__parent',
        'notifiers',
        'service',
        'service__rule_set',
        'service__rule_set__parent',
    )

    def get_context_data(self, **kwargs):
        context = super(ProjectDetail, self).get_context_data(**kwargs)
        context['sources'] = models.Farm.choices()
        context['global'] = models.Service.default()
        prefetch_related_objects([context['global']], 'rule_set')
        return context


class FarmList(ListView):
    queryset = models.Farm.objects\
        .prefetch_related(
            'project_set',
            'host_set',
        )


class FarmDetail(DetailView):
    model = models.Farm


class FarmUpdate(UpdateView):
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


class FarmDelete(RedirectView):
    pattern_name = 'farm-detail'

    def post(self, request, pk):
        farm = get_object_or_404(models.Farm, id=pk)
        farm.delete()

        return HttpResponseRedirect(
            request.POST.get('next', reverse('service-list'))
        )


class UnlinkFarm(View):
    def post(self, request, pk):
        project = get_object_or_404(models.Project, id=pk)
        oldfarm, project.farm = project.farm, None
        project.save()
        signals.trigger_write_config.send(request)

        if oldfarm.project_set.count() == 0 and oldfarm.editable is False:
            logger.debug('Cleaning up old farm %s', oldfarm)
            oldfarm.delete()

        return HttpResponseRedirect(reverse('project-detail', args=[project.id]))


class RulesList(ListView, ServiceMixin):
    template_name = 'promgen/rule_list.html'
    queryset = models.Rule.objects\
        .prefetch_related('content_type', 'content_object')

    def get_context_data(self, **kwargs):
        context = super(RulesList, self).get_context_data(**kwargs)

        service_rules = models.Rule.objects.filter(
            content_type__model='service'
        ).prefetch_related('content_object', 'content_object__shard', 'rulelabel_set', 'ruleannotation_set', 'parent')

        project_rules = models.Rule.objects.filter(
            content_type__model='project'
        ).prefetch_related('content_object', 'content_object__service', 'rulelabel_set', 'ruleannotation_set', 'parent')

        context['rule_list'] = chain(service_rules, project_rules)

        return context


class RulesCopy(View):
    def post(self, request, pk):
        original = get_object_or_404(models.Rule, id=pk)
        form = forms.RuleCopyForm(request.POST)

        if form.is_valid():
            rule = original.copy_to(**form.clean())
            return HttpResponseRedirect(reverse('rule-edit', args=[rule.id]))
        else:
            return HttpResponseRedirect(reverse('service-detail', args=[pk]))


class FarmRefresh(RedirectView):
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


class FarmConvert(RedirectView):
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


class FarmLink(View):
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


class ExporterRegister(FormView, ProjectMixin):
    model = models.Exporter
    template_name = 'promgen/exporter_form.html'
    form_class = forms.ExporterForm

    def get_context_data(self, **kwargs):
        context = super(ExporterRegister, self).get_context_data(**kwargs)
        context['exporters'] = settings.PROMGEN.get('default_exporters', {
            'node': 9100,
            'nginx': 9113,
            'mysqld': 9104,
            'apache': 9117,
        })

        return context

    def form_valid(self, form):
        project = get_object_or_404(models.Project, id=self.kwargs['pk'])
        exporter, _ = models.Exporter.objects.get_or_create(project=project, **form.clean())
        return HttpResponseRedirect(reverse('project-detail', args=[project.id]))


class URLRegister(FormView, ProjectMixin):
    model = models.URL
    template_name = 'promgen/url_form.html'
    form_class = forms.URLForm

    def form_valid(self, form):
        project = get_object_or_404(models.Project, id=self.kwargs['pk'])
        url, _ = models.URL.objects.get_or_create(project=project, **form.clean())
        return HttpResponseRedirect(reverse('project-detail', args=[project.id]))


class URLDelete(DeleteView):
    model = models.URL

    def get_success_url(self):
        return reverse('project-detail', args=[self.object.project_id])


class URLList(ListView):
    queryset = models.URL.objects\
        .prefetch_related(
            'project',
            'project__service',
            'project__service__shard',
        )


class ProjectRegister(FormView, ServiceMixin):
    button_label = _('Project Register')
    model = models.Project
    template_name = 'promgen/project_form.html'
    form_class = forms.ProjectForm

    def form_valid(self, form):
        service = get_object_or_404(models.Service, id=self.kwargs['pk'])
        project, _ = models.Project.objects.get_or_create(service=service, **form.clean())
        return HttpResponseRedirect(reverse('project-detail', args=[project.id]))


class ProjectUpdate(UpdateView):
    model = models.Project
    button_label = _('Project Update')
    template_name = 'promgen/project_form.html'
    form_class = forms.ProjectMove

    def get_context_data(self, **kwargs):
        context = super(ProjectUpdate, self).get_context_data(**kwargs)
        context['service'] = self.object.service
        return context


class ServiceUpdate(UpdateView):
    button_label = _('Update Service')
    form_class = forms.ServiceForm
    model = models.Service
    template_name = 'promgen/service_form.html'


class RuleUpdate(UpdateView):
    queryset = models.Rule.objects.prefetch_related(
        'content_object',
        'overrides',
        'overrides__content_object',
    )
    template_name = 'promgen/rule_update.html'
    form_class = forms.RuleForm

    LabelForm = inlineformset_factory(models.Rule, models.RuleLabel, fields=('name', 'value'), widgets={
        'name': django_forms.TextInput(attrs={'class': 'form-control'}),
        'value': django_forms.TextInput(attrs={'rows': 5, 'class': 'form-control'}),
    })
    AnnotationForm = inlineformset_factory(models.Rule, models.RuleAnnotation, fields=('name', 'value'), widgets={
        'name': django_forms.TextInput(attrs={'class': 'form-control'}),
        'value': django_forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
    })

    def get_context_data(self, **kwargs):
        context = super(RuleUpdate, self).get_context_data(**kwargs)
        context['label_set'] = self.LabelForm(instance=self.object)
        context['annotation_set'] = self.AnnotationForm(instance=self.object)
        context['macro'] = macro.EXCLUSION_MACRO
        if self.object.parent:
            context['rules'] = [self.object.parent]
        else:
            context['rules'] = [self.object]
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        if not form.is_valid():
            return self.form_invalid(form)

        labels = self.LabelForm(request.POST, request.FILES, instance=self.object)
        if labels.is_valid():
            for instance in labels.save():
                messages.info(request, 'Added {} to {}'.format(instance.name, self.object))
        else:
            logger.warning('Error saving labels %s', labels.errors)
            return self.form_invalid(form)

        annotations = self.AnnotationForm(request.POST, request.FILES, instance=self.object)
        if annotations.is_valid():
            for instance in annotations.save():
                messages.info(request, 'Added {} to {}'.format(instance.name, self.object))
        else:
            logger.warning('Error saving annotations %s', annotations.errors)
            return self.form_invalid(form)

        try:
            prometheus.check_rules([form.instance])
        except Exception as e:
            form._update_errors(e)
            return self.form_invalid(form)

        return self.form_valid(form)


class RuleRegister(FormView, ServiceMixin):
    model = models.Rule
    template_name = 'promgen/rule_register.html'
    form_class = forms.NewRuleForm

    def get_context_data(self, **kwargs):
        context = super(RuleRegister, self).get_context_data(**kwargs)
        # Set a dummy rule, so that our header/breadcrumbs render correctly
        context['rule'] = models.Rule()
        context['rule'].pk = 0
        context['rule'].set_object(self.kwargs['content_type'], self.kwargs['object_id'])
        context['macro'] = macro.EXCLUSION_MACRO
        return context

    def post(self, request, content_type, object_id):
        form = self.get_form()
        if form.is_valid():
            form.instance.set_object(content_type, object_id)
            prometheus.check_rules([form.instance])

            try:
                # Set an instance of our service here so that we can pass it
                # along for promtool to render
                form.instance.set_object(content_type, object_id)
                prometheus.check_rules([form.instance])
            except Exception as e:
                form._update_errors(e)
                return self.form_invalid(form)

            form.instance.save()
            return HttpResponseRedirect(form.instance.get_absolute_url())

        if 'rules' not in request.POST:
            return self.form_invalid(form)

        importform = forms.ImportRuleForm(request.POST)
        service = get_object_or_404(models.Service, id=self.kwargs['pk'])
        if importform.is_valid():
            data = importform.clean()
            counters = prometheus.import_rules(data['rules'], service)
            messages.info(request, 'Imported %s' % counters)
            return HttpResponseRedirect(service.get_absolute_url())

        return self.form_invalid(form)


class ServiceRegister(FormView):
    button_label = _('Service Register')
    form_class = forms.ProjectForm
    model = models.Service
    template_name = 'promgen/service_form.html'

    def form_valid(self, form):
        shard = get_object_or_404(models.Shard, id=self.kwargs['pk'])
        service, _ = models.Service.objects.get_or_create(shard=shard, **form.clean())
        return HttpResponseRedirect(service.get_absolute_url())


class FarmRegsiter(FormView, ProjectMixin):
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


class ProjectNotifierRegister(FormView, ProjectMixin):
    model = models.Sender
    template_name = 'promgen/notifier_form.html'
    form_class = forms.SenderForm

    def form_valid(self, form):
        project = get_object_or_404(models.Project, id=self.kwargs['pk'])
        sender, _ = models.Sender.get_or_create(obj=project, **form.clean())
        return HttpResponseRedirect(project.get_absolute_url())


class ServiceNotifierRegister(FormView, ServiceMixin):
    model = models.Sender
    template_name = 'promgen/notifier_form.html'
    form_class = forms.SenderForm

    def form_valid(self, form):
        service = get_object_or_404(models.Service, id=self.kwargs['pk'])
        sender, _ = models.Sender.get_or_create(obj=service, **form.clean())
        return HttpResponseRedirect(service.get_absolute_url())


class HostRegister(FormView):
    model = models.Host
    template_name = 'promgen/host_form.html'
    form_class = forms.HostForm

    def get_context_data(self, **kwargs):
        context = super(HostRegister, self).get_context_data(**kwargs)
        context['farm'] = get_object_or_404(models.Farm, id=self.kwargs['pk'])
        context['project'] = context['farm'].project_set.first()
        return context

    def form_valid(self, form):
        farm = get_object_or_404(models.Farm, id=self.kwargs['pk'])
        for hostname in form.clean()['hosts'].split('\n'):
            hostname = hostname.strip()
            if hostname == '':
                continue

            host, created = models.Host.objects.get_or_create(
                name=hostname,
                farm_id=farm.id,
            )
            if created:
                logger.debug('Added %s to %s', host.name, farm.name)

        return HttpResponseRedirect(reverse('project-detail', args=[farm.project_set.first().id]))


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


class Commit(View):
    def post(self, request):
        signals.trigger_write_config.send(request)
        return HttpResponseRedirect(request.POST.get('next', '/'))


class ServiceTargets(View):
    def get(self, request, pk):
        service = get_object_or_404(models.Service, id=pk)
        return HttpResponse(prometheus.render_config(service=service), content_type='application/json')


class ServiceRules(View):
    def get(self, request, pk):
        service = get_object_or_404(models.Service, id=pk)
        rules = models.Rule.objects.filter(service=service)
        return HttpResponse(prometheus.render_rules(rules), content_type='text/plain; charset=utf-8')


class ProjectTargets(View):
    def get(self, request, pk):
        project = get_object_or_404(models.Project, id=pk)
        return HttpResponse(prometheus.render_config(project=project), content_type='application/json')


class RulesConfig(View):
    def get(self, request):
        return HttpResponse(prometheus.render_rules(), content_type='text/plain; charset=utf-8')

    def post(self, request):
        prometheus.write_rules()
        return HttpResponse('OK', status=202)


class URLConfig(View):
    def get(self, request):
        return HttpResponse(prometheus.render_urls(), content_type='application/json')

    def post(self, request):
        prometheus.write_urls()
        return HttpResponse('OK', status=202)


class Alert(View):
    def post(self, request, *args, **kwargs):
        body = request.body.decode('utf-8')
        for entry in plugins.notifications():
            entry.load().process(body)
        return HttpResponse('OK', status=202)


class Metrics(View):
    version = Gauge('promgen_build_info', 'Promgen Information', ['version', 'python'])
    # Promgen Objects
    exporters = Gauge('promgen_exporters', 'Registered Exporters')
    hosts = Gauge('promgen_hosts', 'Registered Hosts')
    projects = Gauge('promgen_projects', 'Registered Projects')
    rules = Gauge('promgen_rules', 'Registered Rules')
    sender = Gauge('promgen_notifiers', 'Registered Notifiers', ['type', 'sender'])
    services = Gauge('promgen_services', 'Registered Services')
    urls = Gauge('promgen_urls', 'Registered URLs')
    # Celery Queues
    queues = Gauge('promgen_queue_length', 'Queue Size', ['name'])

    def get(self, request, *args, **kwargs):
        self.version.labels(version.__version__, platform.python_version()).set(1)

        for entry in models.Sender.objects.values('content_type__model', 'sender').annotate(Count('sender'), count=Count('content_type')):
            self.sender.labels(entry['content_type__model'], entry['sender']).set(entry['count'])

        self.services.set(models.Service.objects.count())
        self.projects.set(models.Project.objects.count())
        self.exporters.set(models.Exporter.objects.count())
        self.rules.set(models.Rule.objects.count())
        self.urls.set(models.URL.objects.count())
        self.hosts.set(len(models.Host.objects.values('name').annotate(Count('name'))))

        # TODO: This is likely far from optimal and should be re-done in a way
        # that is not redis specific, but this should work for the short term
        if hasattr(settings, 'CELERY_BROKER_URL'):
            with celery.app.connection_for_write() as conn:
                with conn.channel() as channel:
                    for queue in ['celery'] + [host.host for host in models.Prometheus.objects.all()]:
                        self.queues.labels(queue).set(channel.client.llen(queue))

        return HttpResponse(generate_latest(), content_type='text/plain')


class Status(View):
    def get(self, request):
        return render(request, 'promgen/status.html', {
            'discovery_plugins': [entry for entry in plugins.discovery()],
            'notifier_plugins': [entry for entry in plugins.notifications()],
        })


class Search(View):
    def get(self, request):
        return render(request, 'promgen/search.html', {
            'farm_list': models.Farm.objects
                .filter(name__icontains=request.GET.get('search'))
                .prefetch_related('project_set', 'host_set'),
            'host_list': models.Host.objects.filter(name__icontains=request.GET.get('search')),
            'project_list': models.Project.objects
                .filter(name__icontains=request.GET.get('search'))
                .prefetch_related('service', 'notifiers', 'exporter_set'),
            'rule_list': models.Rule.objects
                .filter(
                    Q(name__icontains=request.GET.get('search')) |
                    Q(clause__icontains=request.GET.get('search'))
                )
                .prefetch_related('content_object', 'ruleannotation_set', 'rulelabel_set'),
            'service_list': models.Service.objects
                .filter(name__icontains=request.GET.get('search'))
                .prefetch_related('project_set', 'rule_set', 'notifiers'),
        })


class Import(FormView):
    template_name = 'promgen/import_form.html'
    form_class = forms.ImportConfigForm
    success_url = reverse_lazy('service-list')

    def post(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        form = form_class(request.POST, request.FILES)

        if 'rules' in request.POST:
            form = forms.ImportRuleForm(request.POST)
            if form.is_valid():
                data = form.clean()
                counters = prometheus.import_rules(data['rules'])
                messages.info(request, 'Imported %s' % counters)
                return self.form_valid(form)
            else:
                return self.form_invalid(form)

        if form.is_valid():
            data = form.clean()
            if data.get('file_field'):
                messages.info(request, 'Importing config from file')
                config = data['file_field'].read().decode('utf8')
            elif data.get('url'):
                messages.info(request, 'Importing config from url')
                response = util.get(data['url'])
                response.raise_for_status()
                config = response.text
            else:
                messages.info(request, 'Importing config')
                config = data['config']

            kwargs = {}
            # This also lets us catch passing an empty string to signal using
            # the shard value from the post request
            if data.get('shard'):
                kwargs['replace_shard'] = data.get('shard')

            imported, skipped = prometheus.import_config(json.loads(config), **kwargs)

            if imported:
                counters = {key: len(imported[key]) for key in imported}
                messages.info(request, 'Imported %s' % counters)

            if skipped:
                counters = {key: len(skipped[key]) for key in skipped}
                messages.info(request, 'Skipped %s' % counters)

            # If we only have a single object in a category, automatically
            # redirect to that category to make things easier to understand
            if len(imported['Project']) == 1:
                return HttpResponseRedirect(imported['Project'][0].get_absolute_url())
            if len(imported['Service']) == 1:
                return HttpResponseRedirect(imported['Service'][0].get_absolute_url())
            if len(imported['Shard']) == 1:
                return HttpResponseRedirect(imported['Shard'][0].get_absolute_url())

            # otherwise we can just use the default behavior
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


class Silence(FormView):
    form_class = forms.SilenceForm

    def post(self, request):
        form = forms.SilenceForm(request.POST)
        if form.is_valid():
            # Since it's a little annoying to submit forms with an array, we
            # cheat a bit and just use a simple prefix which we can split on
            # to build our array of labels
            labels = {}
            for key in request.POST:
                if key.startswith('label.'):
                    target = key.split('.', 1)[1]
                    labels[target] = request.POST[key]

            kwargs = {
                'comment': form.cleaned_data['comment'],
                'createdBy': form.cleaned_data['created_by']
            }
            try:
                if form.cleaned_data['duration']:
                    kwargs['duration'] = form.cleaned_data['duration'].lower()
                    prometheus.silence(labels, **kwargs)
                    messages.success(request, 'Setting silence for %s' % form.cleaned_data['duration'])
                else:
                    kwargs['startsAt'] = form.cleaned_data['start']
                    kwargs['endsAt'] = form.cleaned_data['stop']
                    prometheus.silence(labels, **kwargs)
                    messages.success(request, 'Setting silence for %s - %s' % (form.cleaned_data['start'], form.cleaned_data['stop']))
            except Exception as e:
                messages.warning(request, e)
        else:
            messages.warning(request, 'Error setting silence')
        return HttpResponseRedirect(request.POST.get('next', '/'))


class SilenceExpire(FormView):
    form_class = forms.SilenceExpireForm

    def post(self, request):
        form = forms.SilenceExpireForm(request.POST)
        if form.is_valid():
            try:
                silence_id = form.cleaned_data['silence_id']
                url = urljoin(settings.PROMGEN['alertmanager']['url'], '/api/v1/silence/%s' % silence_id)
                util.delete(url).raise_for_status()
                messages.success(request, 'Expire silence')
            except Exception as e:
                messages.warning(request, e)
        else:
            messages.warning(request, 'Error expiring silence')
        return HttpResponseRedirect(request.POST.get('next', '/'))


class AjaxAlert(View):
    def get(self, request):
        alerts = collections.defaultdict(list)
        try:
            url = urljoin(settings.PROMGEN['alertmanager']['url'], '/api/v1/alerts')
            response = util.get(url)
        except requests.exceptions.ConnectionError:
            logger.error('Error connecting to %s', url)
            return JsonResponse({})

        data = response.json().get('data', [])
        if data is None:
            # Return an empty alert-all if there are no active alerts from AM
            return JsonResponse({})
        for alert in data:
            for key in ['startsAt', 'endsAt']:
                if key in alert:
                    alert[key] = parser.parse(alert[key])

            alerts['alert-all'].append(alert)
            for key in ['project', 'service']:
                # Requires newer 0.7 alert manager release to have the status
                # information with silenced and inhibited alerts
                if 'status' in alert:
                    if alert['status'].get('silencedBy') or alert['status'].get('inhibitedBy'):
                        continue
                if key in alert['labels'] and alert['labels'][key]:
                        alerts['alert-{}-{}'.format(key, alert['labels'][key])].append(alert)

        context = {'#' + slugify(key): render_to_string('promgen/ajax_alert.html', {'alerts': alerts[key], 'key': key}, request).strip() for key in alerts}
        context['#alert-load'] = render_to_string('promgen/ajax_alert_button.html', {'alerts': alerts['alert-all'], 'key': 'alert-all'}).strip()

        return JsonResponse(context)


class RuleTest(View):
    def post(self, request, pk):
        if pk == '0':
            rule = models.Rule()
            rule.set_object(request.POST['content_type'], request.POST['object_id'])
        else:
            rule = get_object_or_404(models.Rule, id=pk)

        query = macro.rulemacro(request.POST['query'], rule)

        url = '{}/api/v1/query'.format(rule.service.shard.url)

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


class AjaxSilence(View):
    def post(self, request):
        silences = collections.defaultdict(list)
        try:
            url = urljoin(settings.PROMGEN['alertmanager']['url'], '/api/v1/silences')
            response = util.get(url)
        except requests.exceptions.ConnectionError:
            logger.error('Error connecting to %s', url)
            return JsonResponse({})

        data = response.json().get('data', [])
        if data is None:
            # Return an empty silence-all if there are no active silences from AM
            return JsonResponse({})

        currentAt = datetime.datetime.now(datetime.timezone.utc)

        for silence in data:
            # Since there is no status field, compare endsAt with the current time
            if 'endsAt' in silence:
                silence['endsAt'] = parser.parse(silence['endsAt'])
                if silence['endsAt'] < currentAt:
                    continue

            silences['silence-all'].append(silence)
            for matcher in silence.get('matchers'):
                if matcher.get('name') in ['service', 'project']:
                    silences['silence-{}-{}'.format(matcher.get('name'), matcher.get('value'))].append(silence)

        context = {'#' + slugify(key): render_to_string('promgen/ajax_silence.html', {'silences': silences[key], 'key': key}, request).strip() for key in silences}
        context['#silence-load'] = render_to_string('promgen/ajax_silence_button.html', {'silences': silences['silence-all'], 'key': 'silence-all'}).strip()

        return JsonResponse(context)


class PrometheusProxy(View):
    proxy_headers = [
        # 'CONTENT_TYPE',
        # 'HTTP_ACCEPT_ENCODING',
        # 'HTTP_ACCEPT_LANGUAGE',
        # 'HTTP_ACCEPT',
        'HTTP_REFERER',
    ]

    @property
    def headers(self):
        return {k: self.request.META[k] for k in self.proxy_headers if k in self.request.META}


class ProxyLabel(PrometheusProxy):
    def get(self, request, label):
        data = set()
        futures = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            for host in models.Shard.objects.filter(proxy=True):
                futures.append(executor.submit(util.get, '{}/api/v1/label/{}/values'.format(host.url, label), headers=self.headers))
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    data.update(result.json()['data'])
                except:
                    logger.exception('Missing data result')

        return JsonResponse({
            'status': 'success',
            'data': sorted(data)
        })


class ProxySeries(PrometheusProxy):
    def get(self, request):
        data = []
        futures = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            for host in models.Shard.objects.filter(proxy=True):
                futures.append(executor.submit(util.get, '{}/api/v1/series?{}'.format(host.url, request.META['QUERY_STRING']), headers=self.headers))
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    logger.debug('Appending data from %s', result.request.url)
                    data += result.json()['data']
                except:
                    logger.exception('Missing data result')

        return JsonResponse({
            'status': 'success',
            'data': data
        })


class ProxyQueryRange(PrometheusProxy):
    def get(self, request):
        data = []
        futures = []
        resultType = None
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            for host in models.Shard.objects.filter(proxy=True):
                futures.append(executor.submit(util.get, '{}/api/v1/query_range?{}'.format(host.url, request.META['QUERY_STRING']), headers=self.headers))
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    logger.debug('Appending data from %s', result.request.url)
                    _json = result.json()
                    data += _json['data']['result']
                    resultType = _json['data']['resultType']
                except:
                    logger.exception('Error with response')

        return JsonResponse({
            'status': 'success',
            'data': {
                'resultType': resultType,
                'result': data,
            }
        })
