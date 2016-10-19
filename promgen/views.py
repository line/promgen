from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import DetailView, ListView, View
from django.views.generic.detail import SingleObjectMixin
from promgen import models


class ServiceList(ListView):
    model = models.Service


class HostList(ListView):
    model = models.Host


class ServiceDetail(DetailView):
    model = models.Service


class ProjectDetail(DetailView):
    model = models.Project


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
        return HttpResponseRedirect(reverse('project-detail', args=[project.id]))


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
