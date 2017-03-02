import collections
import datetime
import json
import logging
import time
from urllib.parse import urljoin

import requests
from django import forms as django_forms
from django.conf import settings
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.forms import inlineformset_factory
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils.text import slugify
from django.utils.translation import ugettext as _
from django.views.generic import DetailView, ListView, UpdateView, View
from django.views.generic.base import ContextMixin
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.edit import DeleteView, FormView

from promgen import forms, models, plugins, prometheus, signals, util, version

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


class ShardList(ListView):
    model = models.Shard


class ShardDetail(DetailView):
    queryset = models.Shard.objects\
        .prefetch_related(
            'service_set',
            'service_set__project_set',
            'service_set__project_set__farm',
            'service_set__project_set__exporter_set',
            'service_set__project_set__sender')


class ServiceList(ListView):
    queryset = models.Service.objects\
        .prefetch_related(
            'sender',
            'rule_set',
            'project_set',
            'project_set__farm',
            'project_set__exporter_set',
            'project_set__sender')


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


class HostDetail(DetailView):
    model = models.Host


class HostSearch(ListView):
    template_name = 'promgen/host_search.html'

    def get_queryset(self):
        return models.Host.objects\
            .filter(name__contains=self.kwargs['name'])\
            .prefetch_related(
                'farm',
            )


class AuditList(ListView):
    queryset = models.Audit.objects.order_by('-created')
    paginate_by = 50


class ServiceDetail(DetailView):
    queryset = models.Service.objects\
        .prefetch_related(
            'project_set',
            'project_set__farm',
            'project_set__exporter_set',
            'project_set__sender')


class ServiceDelete(DeleteView):
    model = models.Service

    def get_success_url(self):
        return reverse('shard-detail', args=[self.object.shard_id])


class ProjectDelete(DeleteView):
    model = models.Project

    def get_success_url(self):
        return reverse('service-detail', args=[self.object.service_id])


class SenderDelete(DeleteView):
    model = models.Sender

    def get_success_url(self):
        return self.object.content_object.get_absolute_url()


class SenderTest(View):
    def post(self, request, pk):
        sender = get_object_or_404(models.Sender, id=pk)
        for entry in plugins.senders():
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


class RuleDelete(DeleteView):
    model = models.Rule

    def get_success_url(self):
        return reverse('service-detail', args=[self.object.service_id])


class RuleToggle(View):
    def post(self, request, pk):
        rule = get_object_or_404(models.Rule, id=pk)
        rule.enabled = not rule.enabled
        rule.save()
        return HttpResponseRedirect(reverse('service-detail', args=[rule.service_id]))


class HostDelete(DeleteView):
    model = models.Host

    def get_success_url(self):
        return reverse('project-detail', args=[self.object.farm.project_set.first().id])


class ProjectDetail(DetailView):
    model = models.Project

    def get_context_data(self, **kwargs):
        context = super(ProjectDetail, self).get_context_data(**kwargs)
        context['sources'] = [
            entry.name for entry in plugins.remotes()
        ]
        context['global'] = models.Service.default()
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


class FarmDelete(DeleteView):
    model = models.Farm

    def get_success_url(self):
        return reverse('service-list')


class UnlinkFarm(View):
    def post(self, request, pk):
        project = get_object_or_404(models.Project, id=pk)
        project.farm = None
        project.save()
        signals.trigger_write_config.send(self)
        return HttpResponseRedirect(reverse('project-detail', args=[project.id]))


class RulesList(ListView, ServiceMixin):
    template_name = 'promgen/rule_list.html'

    def get_queryset(self):
        if 'pk' in self.kwargs:
            self.service = get_object_or_404(models.Service, id=self.kwargs['pk'])
            return models.Rule.objects.filter(service=self.service)
        return models.Service.objects\
            .prefetch_related('rule_set')


class RulesCopy(View):
    def post(self, request, pk):
        service = get_object_or_404(models.Service, id=pk)
        form = forms.RuleCopyForm(request.POST)

        if form.is_valid():
            data = form.clean()
            rule = get_object_or_404(models.Rule, id=data['rule_id'])
            rule.copy_to(service)
            return HttpResponseRedirect(reverse('rule-edit', args=[rule.id]))
        else:
            return HttpResponseRedirect(reverse('service-detail', args=[pk]))


class FarmRefresh(SingleObjectMixin, View):
    model = models.Farm

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.refresh()
        project = self.object.project_set.get()
        models.Audit.log('Refreshed Farm')
        return HttpResponseRedirect(reverse('project-detail', args=[project.id]))


class FarmConvert(SingleObjectMixin, View):
    model = models.Farm

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.source = models.FARM_DEFAULT
        self.object.save()
        return HttpResponseRedirect(reverse('farm-detail', args=[self.object.id]))


class FarmLink(View):
    def get(self, request, pk, source):
        context = {
            'source': source,
            'project': get_object_or_404(models.Project, id=pk),
            'farms': models.Farm.fetch(source=source),
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
    model = models.Rule
    template_name = 'promgen/rule_form.html'
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
        context['service'] = self.object.service
        context['label_set'] = self.LabelForm(instance=self.object)
        context['annotation_set'] = self.AnnotationForm(instance=self.object)
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

        return self.form_valid(form)


class RuleRegister(FormView, ServiceMixin):
    model = models.Rule
    template_name = 'promgen/rule_register.html'
    form_class = forms.NewRuleForm
    rule_copy_form = forms.RuleCopyForm()

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
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

    def form_valid(self, form):
        service = get_object_or_404(models.Service, id=self.kwargs['pk'])
        rule, _ = models.Rule.objects.get_or_create(service=service, **form.clean())
        return HttpResponseRedirect(reverse('rule-edit', args=[rule.id]))


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
        farm, _ = models.Farm.objects.get_or_create(source=models.FARM_DEFAULT, **form.clean())
        project.farm = farm
        project.save()
        return HttpResponseRedirect(project.get_absolute_url())


class ProjectSenderRegister(FormView, ProjectMixin):
    model = models.Sender
    template_name = 'promgen/sender_form.html'
    form_class = forms.SenderForm

    def form_valid(self, form):
        project = get_object_or_404(models.Project, id=self.kwargs['pk'])
        project_type = ContentType.objects.get_for_model(project)
        sender, _ = models.Sender.objects.get_or_create(object_id=project.id, content_type_id=project_type.id, **form.clean())
        return HttpResponseRedirect(project.get_absolute_url())


class ServiceSenderRegister(FormView, ServiceMixin):
    model = models.Sender
    template_name = 'promgen/service_sender_form.html'
    form_class = forms.SenderForm

    def form_valid(self, form):
        service = get_object_or_404(models.Service, id=self.kwargs['pk'])
        service_type = ContentType.objects.get_for_model(service)
        sender, _ = models.Sender.objects.get_or_create(object_id=service.id, content_type_id=service_type.id, **form.clean())
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

    def post(self, request):
        prometheus.write_config()
        return HttpResponse('OK', status=202)


class Commit(View):
    def post(self, request):
        signals.trigger_write_config.send(self)
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
        body = json.loads(request.body.decode('utf-8'))

        for entry in plugins.senders():
            logger.debug('Sending notification to %s', entry.name)
            sent = 0
            error = 0
            try:
                Sender = entry.load()
                logger.debug(Sender)
                Sender().send(body)
            except Exception:
                logger.exception('Error sending alert')
                error += 1
            else:
                sent += 1
        return HttpResponse('OK')


class Metrics(View):
    def get(self, request, *args, **kwargs):
        return HttpResponse('promgen_build_info{{version="{}"}} 1\n'.format(version.__version__), content_type='text/plain')


class Status(View):
    def get(self, request):
        return render(request, 'promgen/status.html', {
            'remotes': [entry for entry in plugins.remotes()],
            'senders': [entry for entry in plugins.senders()],
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
                .prefetch_related('service', 'sender', 'exporter_set'),
            'rule_list': models.Rule.objects
                .filter(
                    Q(name__icontains=request.GET.get('search')) |
                    Q(clause__icontains=request.GET.get('search'))
                )
                .prefetch_related('service'),
            'service_list': models.Service.objects
                .filter(name__icontains=request.GET.get('search'))
                .prefetch_related('project_set', 'rule_set', 'sender'),
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
                response = requests.get(data['url'])
                response.raise_for_status()
                config = response.text
            else:
                messages.info(request, 'Importing config')
                config = data['config']

            counters = prometheus.import_config(json.loads(config))
            messages.info(request, 'Imported %s' % counters)

            return self.form_valid(form)
        else:
            return self.form_invalid(form)


class Mute(FormView):
    form_class = forms.MuteForm

    def get(self, request, **kwargs):
        context = {}
        MAPPING = {
            'farm': models.Farm,
            'host': models.Host,
            'project': models.Project,
            'service': models.Service,
        }
        for label, klass in MAPPING.items():
            if label in kwargs:
                context['label'] = label
                # TODO: using isnumeric sees fragile but I can revisit later
                if kwargs[label].isnumeric():
                    context['obj'] = klass.objects.filter(pk=kwargs[label]).first()
                else:
                    context['obj'] = klass.objects.filter(name=kwargs[label]).first()
        if context:
            return render(request, 'promgen/mute_form.html', context)
        return HttpResponseRedirect('/')

    def post(self, request):
        form = forms.MuteForm(request.POST)
        if form.is_valid():
            # Since it's a little annoying to submit forms with an array, we
            # cheat a bit and just use a simple prefix which we can split on
            # to build our array of labels
            labels = {}
            for key in request.POST:
                if key.startswith('label.'):
                    target = key.split('.', 1)[1]
                    labels[target] = request.POST[key]
            try:
                duration = form.cleaned_data['duration']
                if duration:
                    prometheus.mute(duration, labels)
                    messages.success(request, 'Setting mute for %s' % duration)
                else:
                    start = form.cleaned_data['start']
                    stop = form.cleaned_data['stop']
                    prometheus.mute_fromto(start, stop, labels)
                    messages.success(request, 'Setting mute for %s - %s' % (start, stop))
            except Exception as e:
                messages.warning(request, e)
        else:
            messages.warning(request, 'Error setting mute')
        return HttpResponseRedirect(request.POST.get('next', '/'))


class AjaxAlert(View):
    def get(self, request):
        alerts = collections.defaultdict(list)
        url = urljoin(settings.PROMGEN['alertmanager']['url'], '/api/v1/alerts/groups')
        response = requests.get(url)
        data = response.json().get('data', [])
        if data is None:
            # Return an empty alert-all if there are no active alerts from AM
            return JsonResponse({'alert-all': ''})
        for group in data:
            if group.get('blocks') is None:
                continue
            for block in group.get('blocks', []):
                for alert in block.get('alerts', []):
                    if alert.get('silenced', False):
                        continue
                    if alert['labels'].get('alertname') == 'PromgenHeartbeat':
                        continue
                    alerts['alert-all'].append(alert)
                    for key in ['project', 'service']:
                        if key in alert['labels']:
                            if alert['labels'][key]:
                                alerts['alert-{}-{}'.format(key, alert['labels'][key])].append(alert)

        alerts = {'#' + slugify(key): render_to_string('promgen/ajax_alert.html', {'alerts': alerts[key], 'key': key}, request) for key in alerts}
        if '#alert-all' not in alerts:
            alerts['#alert-all'] = render_to_string('promgen/ajax_alert_clear.html')

        return JsonResponse(alerts)


class AjaxClause(View):
    def post(self, request):
        url = '{}api/v1/query'.format(
            settings.PROMGEN['prometheus']['url']
        )

        query = request.POST['query']
        shard = get_object_or_404(models.Shard, id=request.POST['shard'])

        logger.debug('Querying %s with %s', url, query)
        start = time.time()
        result = util.get(url, {'query': request.POST['query']}).json()
        duration = datetime.timedelta(seconds=(time.time() - start))

        context = {'status': result['status'], 'duration': duration}
        context['data'] = result.get('data', {})

        context['errors'] = {}

        metrics = context['data'].get('result', [])
        if metrics:
            for row in metrics:
                if 'service' not in row['metric'] and \
                        'project' not in row['metric']:
                    context['errors']['routing'] = 'Missing service and project labels so Promgen will be unable to route message'
                    context['status'] = 'warning'
        else:
            context['status'] = 'info'
            context['errors']['no_results'] = 'No Results. May need to remove conditional check (> < ==) to verity'

        # Place this at the bottom to have a query error show up as danger
        if result['status'] != 'success':
            context['status'] = 'danger'
            context['errors']['Query'] = result['error']

        return JsonResponse({'#ajax-clause-check': render_to_string('promgen/ajax_clause_check.html', context)})
