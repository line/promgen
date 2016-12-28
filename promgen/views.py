import collections
import json
import logging

import requests
from django.conf import settings
from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse, reverse_lazy
from django.utils.translation import ugettext as _
from django.views.generic import DetailView, ListView, UpdateView, View
from django.views.generic.base import ContextMixin
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.edit import DeleteView, FormView

from promgen import forms, models, plugins, prometheus, signals

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


class ServiceList(ListView):
    queryset = models.Service.objects\
        .prefetch_related(
            'project_set',
            'project_set__farm',
            'project_set__exporter_set',
            'project_set__sender_set')


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
            'project_set__sender_set')


class ServiceDelete(DeleteView):
    model = models.Service
    success_url = reverse_lazy('service-list')


class ProjectDelete(DeleteView):
    model = models.Project

    def get_success_url(self):
        return reverse('service-detail', args=[self.object.service_id])


class SenderDelete(DeleteView):
    model = models.Sender

    def get_success_url(self):
        return reverse('project-detail', args=[self.object.project_id])


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
                    messages.warning(request, 'Error sending test message with ' + entry.module_name)
                else:
                    messages.info(request, 'Sent test message with ' + entry.module_name)

        return HttpResponseRedirect(reverse('project-detail', args=[sender.project.id]))


class ExporterDelete(DeleteView):
    model = models.Exporter

    def get_success_url(self):
        return reverse('project-detail', args=[self.object.project_id])


class RuleDelete(DeleteView):
    model = models.Rule

    def get_success_url(self):
        return reverse('service-rules', args=[self.object.service_id])


class RuleToggle(View):
    def post(self, request, pk):
        rule = get_object_or_404(models.Rule, id=pk)
        rule.enabled = not rule.enabled
        rule.save()
        return HttpResponseRedirect(reverse('service-rules', args=[rule.service_id]))


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
    model = models.Rule

    def get_queryset(self):
        if 'pk' in self.kwargs:
            self.service = get_object_or_404(models.Service, id=self.kwargs['pk'])
            return models.Rule.objects.filter(service=self.service)
        return models.Rule.objects.all()

    def get_context_data(self, **kwargs):
        context = super(RulesList, self).get_context_data(**kwargs)
        context['all_rules'] = models.Rule.objects.all()
        return context


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
    model = models.Project
    template_name = 'promgen/project_form.html'
    form_class = forms.ProjectForm

    def form_valid(self, form):
        service = get_object_or_404(models.Service, id=self.kwargs['pk'])
        project, _ = models.Project.objects.get_or_create(service=service, **form.clean())
        return HttpResponseRedirect(reverse('project-detail', args=[project.id]))


class ProjectUpdate(UpdateView):
    model = models.Project
    template_name = 'promgen/project_form.html'
    form_class = forms.ProjectForm

    def get_context_data(self, **kwargs):
        context = super(ProjectUpdate, self).get_context_data(**kwargs)
        context['service'] = self.object.service
        return context


class ServiceUpdate(UpdateView):
    model = models.Service
    template_name = 'promgen/service_form.html'
    form_class = forms.ServiceForm


class RuleUpdate(UpdateView):
    model = models.Rule
    template_name = 'promgen/rule_form.html'
    form_class = forms.RuleForm

    def get_context_data(self, **kwargs):
        context = super(RuleUpdate, self).get_context_data(**kwargs)
        context['service'] = self.object.service
        return context

    def get_success_url(self):
        return reverse('service-rules', args=[self.object.service_id])


class RuleRegister(FormView, ServiceMixin):
    model = models.Rule
    template_name = 'promgen/rule_form.html'
    form_class = forms.RuleForm

    def form_valid(self, form):
        service = get_object_or_404(models.Service, id=self.kwargs['pk'])
        rule, _ = models.Rule.objects.get_or_create(service=service, **form.clean())
        return HttpResponseRedirect(reverse('service-rules', args=[service.id]))


class ServiceRegister(FormView):
    model = models.Service
    template_name = 'promgen/service_form.html'
    form_class = forms.ProjectForm

    def form_valid(self, form):
        service, _ = models.Service.objects.get_or_create(**form.clean())
        return HttpResponseRedirect(reverse('service-detail', args=[service.id]))


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
        return HttpResponseRedirect(reverse('project-detail', args=[project.id]))


class SenderRegister(FormView, ProjectMixin):
    model = models.Sender
    template_name = 'promgen/sender_form.html'
    form_class = forms.SenderForm

    def form_valid(self, form):
        project = get_object_or_404(models.Project, id=self.kwargs['pk'])
        sender, _ = models.Sender.objects.get_or_create(project=project, **form.clean())
        return HttpResponseRedirect(reverse('project-detail', args=[project.id]))


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


class ServiceExport(View):
    def get(self, request, pk):
        service = get_object_or_404(models.Service, id=pk)
        return HttpResponse(prometheus.render_config(service=service), content_type='application/json')


class ProjectExport(View):
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
                if entry.load()().send(body):
                    sent += 1
            except Exception:
                logger.exception('Error sending alert')
                error += 1
        return HttpResponse('OK')


class Metrics(View):
    def get(self, request, *args, **kwargs):
        return HttpResponse('', content_type='text/plain')


class Status(View):
    def get(self, request):
        return render(request, 'promgen/status.html', {
            'remotes': [entry for entry in plugins.remotes()],
            'senders': [entry for entry in plugins.senders()],
        })


class Search(View):
    def get(self, request):
        return render(request, 'promgen/search.html', {
            'farm_list': models.Farm.objects.filter(name__icontains=request.GET.get('search')),
            'host_list': models.Host.objects.filter(name__icontains=request.GET.get('search')),
            'project_list': models.Project.objects.filter(name__icontains=request.GET.get('search')),
            'rule_list': models.Rule.objects.filter(
                Q(name__icontains=request.GET.get('search')) |
                Q(clause__icontains=request.GET.get('search'))
            ),
            'service_list': models.Service.objects.filter(name__icontains=request.GET.get('search')),
        })


class Import(FormView):
    template_name = 'promgen/import_form.html'
    form_class = forms.ImportForm
    success_url = reverse_lazy('service-list')

    def post(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        form = form_class(request.POST, request.FILES)

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
                duration = form.clean()['duration']
                prometheus.mute(duration, labels)
                messages.success(request, 'Setting mute for %s' % duration)
            except Exception as e:
                messages.warning(request, e)
        else:
            messages.warning(request, 'Error setting mute')
        return HttpResponseRedirect(request.POST.get('next', '/'))
