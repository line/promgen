from django.conf import settings
from django.http import HttpResponse
from promgen import models, prometheus, serializers
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response


class ShardViewSet(viewsets.ModelViewSet):
    queryset = models.Shard.objects.all()
    serializer_class = serializers.ShardSerializer
    lookup_field = 'name'

    @action(detail=True, methods=['get'])
    def services(self, request, name):
        shard = self.get_object()
        return Response(
            serializers.ServiceSerializer(shard.service_set.all(), many=True).data
        )


class SharedViewSet:
    def format(self, rules=None, name='promgen'):
        version = settings.PROMGEN['prometheus'].get('version', 1)
        content = prometheus.render_rules(rules, version=version)
        response = HttpResponse(content)
        if version == 1:
            response['Content-Type'] = 'text/plain; charset=utf-8'
            response['Content-Disposition'] = 'attachment; filename=%s.rule' % name
        else:
            response['Content-Type'] = 'application/x-yaml'
            response['Content-Disposition'] = 'attachment; filename=%s.rule.yml' % name
        return response


class ServiceViewSet(SharedViewSet, viewsets.ModelViewSet):
    queryset = models.Service.objects.prefetch_related('shard')
    serializer_class = serializers.ServiceSerializer
    lookup_value_regex = '[^/]+'
    lookup_field = 'name'

    @action(detail=True, methods=['get'])
    def projects(self, request, name):
        service = self.get_object()
        return Response(
            serializers.ProjectSerializer(service.project_set.all(), many=True).data
        )

    @action(detail=True, methods=['get'])
    def targets(self, request, name):
        return HttpResponse(
            prometheus.render_config(service=self.get_object()),
            content_type='application/json',
        )

    @action(detail=True, methods=['get'])
    def rules(self, request, name):
        rules = models.Rule.filter(obj=self.get_object())
        return self.format(rules)

    @action(detail=True, methods=['get'])
    def notifiers(self, request, name):
        return Response(
            serializers.SenderSerializer(
                self.get_object().notifiers.all(), many=True
            ).data
        )


class ProjectViewSet(SharedViewSet, viewsets.ModelViewSet):
    queryset = models.Project.objects.prefetch_related(
        'service', 'service__shard', 'farm'
    )
    serializer_class = serializers.ProjectSerializer
    lookup_value_regex = '[^/]+'
    lookup_field = 'name'

    @action(detail=True, methods=['get'])
    def targets(self, request, name):
        return HttpResponse(
            prometheus.render_config(project=self.get_object()),
            content_type='application/json',
        )

    @action(detail=True, methods=['get'])
    def rules(self, request, name):
        rules = models.Rule.filter(obj=self.get_object())
        return self.format(rules)

    @action(detail=True, methods=['get'])
    def notifiers(self, request, name):
        return Response(
            serializers.SenderSerializer(
                self.get_object().notifiers.all(), many=True
            ).data
        )
