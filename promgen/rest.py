# Copyright (c) 2019 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from promgen import filters, models, renderers, serializers


class AllViewSet(viewsets.ViewSet):
    permission_classes = [permissions.AllowAny]

    @action(detail=False, renderer_classes=[renderers.RuleRenderer])
    def rules(self, request):
        rules = models.Rule.objects
        return Response(
            serializers.AlertRuleSerializer(rules, many=True).data,
            headers={"Content-Disposition": "attachment; filename=alert.rule.yml"},
        )

    @action(detail=False, renderer_classes=[renderers.ScrapeRenderer])
    def urls(self, request):
        return Response(
            serializers.UrlSeralizer(models.URL.objects.all(), many=True).data
        )

    @action(detail=False, renderer_classes=[renderers.ScrapeRenderer])
    def targets(self, request):
        return Response(
            serializers.TargetSeralizer(models.Exporter.objects, many=True).data
        )


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


class RuleMixin:
    @action(detail=True, methods=["get"], renderer_classes=[renderers.RuleRenderer])
    def rules(self, request, name):
        rules = models.Rule.objects.filter(obj=self.get_object())
        return Response(
            serializers.AlertRuleSerializer(rules, many=True).data,
            headers={"Content-Disposition": "attachment; filename=%s.rule.yml" % name},
        )


class NotifierMixin:
    @action(detail=True, methods=["get"])
    def notifiers(self, request, name):
        return Response(
            serializers.SenderSerializer(
                self.get_object().notifiers.all(), many=True
            ).data
        )


class ServiceViewSet(NotifierMixin, RuleMixin, viewsets.ModelViewSet):
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

    @action(detail=True)
    def targets(self, request, name):
        return Response(
            serializers.TargetSeralizer(
                models.Exporter.objects.filter(project__service__name=name), many=True
            ).data
        )


class ProjectViewSet(NotifierMixin, RuleMixin, viewsets.ModelViewSet):
    queryset = models.Project.objects.prefetch_related("service", "shard", "farm")
    filterset_class = filters.ProjectFilter
    serializer_class = serializers.ProjectSerializer
    lookup_value_regex = "[^/]+"
    lookup_field = "name"

    @action(detail=True)
    def targets(self, request, name):
        return Response(
            serializers.TargetSeralizer(
                models.Exporter.objects.filter(project__name=name), many=True
            ).data
        )

    @action(detail=True, renderer_classes=[renderers.ScrapeRenderer])
    def urls(self, request, name):
        return Response(
            serializers.UrlSeralizer(self.get_object().url_set.all(), many=True).data
        )

    @urls.mapping.post
    def post_url(self, request, name):
        raise NotImplementedError("TODO")
