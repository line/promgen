from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from django.http import HttpResponse

from promgen import filters, models, prometheus, renderers, serializers


class ShardViewSet(viewsets.ModelViewSet):
    queryset = models.Shard.objects.all()
    filterset_class = filters.ShardFilter
    serializer_class = serializers.ShardSerializer
    lookup_field = "name"

    @action(detail=True, methods=["get"])
    def services(self, request, name):
        shard = self.get_object()
        return Response(
            serializers.ServiceSerializer(shard.service_set.all(), many=True).data
        )


class ServiceViewSet(viewsets.ModelViewSet):
    queryset = models.Service.objects.all()
    filterset_class = filters.ServiceFilter
    serializer_class = serializers.ServiceSerializer
    lookup_value_regex = "[^/]+"
    lookup_field = "name"

    @action(detail=True, methods=["get"])
    def projects(self, request, name):
        service = self.get_object()
        return Response(
            serializers.ProjectSerializer(service.project_set.all(), many=True).data
        )

    @action(detail=True, methods=["get"])
    def targets(self, request, name):
        return HttpResponse(
            prometheus.render_config(service=self.get_object()),
            content_type="application/json",
        )

    @action(detail=True, methods=["get"], renderer_classes=[renderers.RuleRenderer])
    def rules(self, request, name):
        rules = models.Rule.objects.filter(obj=self.get_object())
        return Response(serializers.AlertRuleSerializer(rules, many=True).data)

    @action(detail=True, methods=["get"])
    def notifiers(self, request, name):
        return Response(
            serializers.SenderSerializer(
                self.get_object().notifiers.all(), many=True
            ).data
        )


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = models.Project.objects.prefetch_related("service", "shard", "farm")
    filterset_class = filters.ProjectFilter
    serializer_class = serializers.ProjectSerializer
    lookup_value_regex = "[^/]+"
    lookup_field = "name"

    @action(detail=True, methods=["get"])
    def targets(self, request, name):
        return HttpResponse(
            prometheus.render_config(project=self.get_object()),
            content_type="application/json",
        )

    @action(detail=True, methods=["get"], renderer_classes=[renderers.RuleRenderer])
    def rules(self, request, name):
        rules = models.Rule.objects.filter(obj=self.get_object())
        return Response(serializers.AlertRuleSerializer(rules, many=True).data)

    @action(detail=True, methods=["get"])
    def notifiers(self, request, name):
        return Response(
            serializers.SenderSerializer(
                self.get_object().notifiers.all(), many=True
            ).data
        )
