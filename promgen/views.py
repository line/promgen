import json
import logging

from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse, reverse_lazy
from django.views.generic import DetailView, ListView, View
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.edit import DeleteView, FormView
from pkg_resources import working_set

from promgen import forms, models

logger = logging.getLogger(__name__)


class ServiceList(ListView):
    queryset = models.Service.objects\
        .prefetch_related(
            'project_set',
            'project_set__farm',
            'project_set__exporter_set',
            'project_set__sender_set')


class HostList(ListView):
    model = models.Host


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


class ExporterDelete(DeleteView):
    model = models.Exporter

    def get_success_url(self):
        return reverse('project-detail', args=[self.object.project_id])


class RuleDelete(DeleteView):
    model = models.Rule

    def get_success_url(self):
        return reverse('service-rules', args=[self.object.service_id])


class ProjectDetail(DetailView):
    model = models.Project

    def get_context_data(self, **kwargs):
        context = super(ProjectDetail, self).get_context_data(**kwargs)
        context['sources'] = [
            entry.name for entry in working_set.iter_entry_points('promgen.server')
        ]
        return context


class UnlinkFarm(View):
    def post(self, request, pk):
        project = get_object_or_404(models.Project, id=pk)
        project.farm = None
        project.save()
        return HttpResponseRedirect(reverse('project-detail', args=[project.id]))


class RulesList(ListView):
    model = models.Rule

    def get_queryset(self):
        if 'pk' in self.kwargs:
            self.service = get_object_or_404(models.Service, id=self.kwargs['pk'])
            return models.Rule.objects.filter(service=self.service)
        return models.Rule.objects.all()

    def get_context_data(self, **kwargs):
        context = super(RulesList, self).get_context_data(**kwargs)
        if 'pk' in self.kwargs:
            context['service'] = self.service
        return context


class FarmRefresh(SingleObjectMixin, View):
    model = models.Farm

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.refresh()
        project = self.object.project_set.get()
        models.Audit.log('Refreshed Farm')
        return HttpResponseRedirect(reverse('project-detail', args=[project.id]))


class RuleUpdate(View):
    pass


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


class RegisterExporter(FormView):
    model = models.Exporter
    template_name = 'promgen/exporter_form.html'
    form_class = forms.ExporterForm

    def get_context_data(self, **kwargs):
        context = super(RegisterExporter, self).get_context_data(**kwargs)
        if 'pk' in self.kwargs:
            context['project'] = \
                get_object_or_404(models.Project, id=self.kwargs['pk'])

        context['exporters'] = [
            ('node', '9100', ''),
            ('nginx', '9113', ''),
        ]

        return context

    def form_valid(self, form):
        project = get_object_or_404(models.Project, id=self.kwargs['pk'])
        exporter, _ = models.Exporter.objects.get_or_create(project=project, **form.clean())
        return HttpResponseRedirect(reverse('project-detail', args=[project.id]))


class RegisterProject(FormView):
    model = models.Project
    template_name = 'promgen/project_form.html'
    form_class = forms.ProjectForm

    def get_context_data(self, **kwargs):
        context = super(RegisterProject, self).get_context_data(**kwargs)
        if 'pk' in self.kwargs:
            context['service'] = \
                get_object_or_404(models.Service, id=self.kwargs['pk'])

        return context

    def form_valid(self, form):
        service = get_object_or_404(models.Service, id=self.kwargs['pk'])
        project, _ = models.Project.objects.get_or_create(service=service, **form.clean())
        return HttpResponseRedirect(reverse('project-detail', args=[project.id]))


class RegisterRule(FormView):
    model = models.Rule
    template_name = 'promgen/rule_form.html'
    form_class = forms.RuleForm

    def get_context_data(self, **kwargs):
        context = super(RegisterRule, self).get_context_data(**kwargs)
        if 'pk' in self.kwargs:
            context['service'] = \
                get_object_or_404(models.Service, id=self.kwargs['pk'])

        return context

    def form_valid(self, form):
        service = get_object_or_404(models.Service, id=self.kwargs['pk'])
        rule, _ = models.Rule.objects.get_or_create(service=service, **form.clean())
        return HttpResponseRedirect(reverse('service-rules', args=[service.id]))


class RegisterService(FormView):
    model = models.Service
    template_name = 'promgen/service_form.html'
    form_class = forms.ProjectForm

    def form_valid(self, form):
        service, _ = models.Service.objects.get_or_create(**form.clean())
        return HttpResponseRedirect(reverse('service-detail', args=[service.id]))


class RegisterFarm(FormView):
    model = models.Farm
    template_name = 'promgen/farm_form.html'
    form_class = forms.FarmForm

    def get_context_data(self, **kwargs):
        context = super(RegisterFarm, self).get_context_data(**kwargs)
        context['project'] = get_object_or_404(models.Project, id=self.kwargs['pk'])
        return context

    def form_valid(self, form):
        project = get_object_or_404(models.Project, id=self.kwargs['pk'])
        farm, _ = models.Farm.objects.get_or_create(source='default', **form.clean())
        project.farm = farm
        project.save()
        return HttpResponseRedirect(reverse('project-detail', args=[project.id]))


class RegisterHost(FormView):
    model = models.Host
    template_name = 'promgen/host_form.html'
    form_class = forms.HostForm

    def get_context_data(self, **kwargs):
        context = super(RegisterHost, self).get_context_data(**kwargs)
        context['farm'] = get_object_or_404(models.Farm, id=self.kwargs['pk'])
        context['project'] = context['farm'].project_set.first()
        return context

    def form_valid(self, form):
        farm = get_object_or_404(models.Farm, id=self.kwargs['pk'])
        for hostname in form.clean()['hosts'].strip().split('\n'):
            host, created = models.Host.objects.get_or_create(
                name=hostname,
                farm=farm,
            )
            if created:
                logger.debug('Added %s to %s', host.name, farm.name)

        return HttpResponseRedirect(reverse('project-detail', args=[farm.project_set.first().id]))


class ApiConfig(View):
    def get(self, request):
        data = []
        for exporter in models.Exporter.objects.all():
            labels = {
                'project': exporter.project.name,
                'service': exporter.project.service.name,
                'farm': exporter.project.farm.name,
                'job': exporter.job,
            }
            if exporter.path:
                labels['__metrics_path__'] = exporter.path

            hosts = []
            for host in models.Host.objects.filter(farm=exporter.project.farm):
                hosts.append('{}:{}'.format(host.name, exporter.port))

            data.append({
                'labels': labels,
                'targets': hosts,
            })

        return JsonResponse(data, safe=False)


class Alert(View):
    def post(self, request, *args, **kwargs):
        body = json.loads(request.body.decode('utf-8'))

        for entry in working_set.iter_entry_points('promgen.sender'):
            logger.debug('Sending notification to %s', entry.name)
            entry.load().send(body)
        return HttpResponse('OK')
