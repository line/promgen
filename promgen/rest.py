# Copyright (c) 2019 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE
from itertools import chain

from django.http import HttpResponse
from requests.exceptions import HTTPError
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from promgen import filters, models, permissions, prometheus, renderers, serializers, tasks, util
from promgen.permissions import PromgenModelPermissions


class AlertReceiver(APIView):
    permission_classes = [PromgenModelPermissions]
    permissions_required = ["promgen.process_alert"]
    any_perm = True

    def post(self, request, *args, **kwargs):
        # Normally it would be more 'correct' to check our 'alert_blacklist' here and avoid
        # writing to the database, but to keep the alert ingestion queue as simple as possible
        # we will go ahead and write all alerts to the database and then filter out (delete)
        # when we run tasks.process_alert
        alert = models.Alert.objects.create(body=request.body.decode("utf-8"))
        tasks.process_alert.delay(alert.pk)
        return HttpResponse("OK", status=202)


class AllViewSet(viewsets.ViewSet):
    @action(detail=False, methods=["get"], renderer_classes=[renderers.RuleRenderer])
    def rules(self, request):
        site_rules = models.Rule.objects.filter(
            content_type__model="site", content_type__app_label="promgen", enabled=True
        )
        service_rules = models.Rule.objects.filter(
            content_type__model="service", content_type__app_label="promgen", enabled=True
        )
        project_rules = models.Rule.objects.filter(
            content_type__model="project", content_type__app_label="promgen", enabled=True
        )

        # If the user is not a superuser, we need to filter the rules by the user's permissions
        if not self.request.user.is_superuser:
            services = permissions.get_accessible_services_for_user(self.request.user)
            service_rules = service_rules.filter(object_id__in=services)

            projects = permissions.get_accessible_projects_for_user(self.request.user)
            project_rules = project_rules.filter(object_id__in=projects)

        rules = list(chain(site_rules, service_rules, project_rules))
        return Response(
            serializers.AlertRuleSerializer(rules, many=True).data,
            headers={"Content-Disposition": "attachment; filename=alert.rule.yml"},
        )

    @action(detail=False, methods=["get"], renderer_classes=[renderers.renderers.JSONRenderer])
    def targets(self, request):
        if self.request.user.is_superuser:
            return HttpResponse(
                prometheus.render_config(),
                content_type="application/json",
            )

        # if the user is not a superuser, we need to filter the targets by the user's permissions
        services = permissions.get_accessible_services_for_user(self.request.user)
        projects = permissions.get_accessible_projects_for_user(self.request.user)
        farms = models.Farm.objects.filter(project__in=projects)

        return HttpResponse(
            prometheus.render_config(services=services, projects=projects, farms=farms),
            content_type="application/json",
        )

    @action(detail=False, methods=["get"], renderer_classes=[renderers.renderers.JSONRenderer])
    def urls(self, request):
        if self.request.user.is_superuser:
            return HttpResponse(
                prometheus.render_urls(),
                content_type="application/json",
            )

        # if the user is not a superuser, we need to filter the URLs by the user's permissions
        projects = permissions.get_accessible_projects_for_user(self.request.user)

        return HttpResponse(
            prometheus.render_urls(projects=projects),
            content_type="application/json",
        )


class ShardViewSet(viewsets.ModelViewSet):
    queryset = models.Shard.objects.all()
    filterset_class = filters.ShardFilter
    serializer_class = serializers.ShardSerializer
    lookup_field = "name"

    @action(detail=True, methods=["get"])
    def services(self, request, name):
        shard = self.get_object()
        return Response(serializers.ServiceSerializer(shard.service_set.all(), many=True).data)

    @action(detail=True, methods=["get"])
    def usages(self, request, name):
        metric = request.query_params.get("metric", None)
        METRIC_QUERY_MAPPING = {
            "samples": "sum(scrape_samples_scraped)",
            "exporters": "count(up)",
        }
        if metric not in METRIC_QUERY_MAPPING:
            return HttpResponse("BAD REQUEST", status=400)

        shard = self.get_object()
        params = {"query": METRIC_QUERY_MAPPING[request.GET["metric"]]}
        headers = {}

        if shard.authorization:
            headers["Authorization"] = shard.authorization

        try:
            response = util.get(f"{shard.url}/api/v1/query", params=params, headers=headers)
            response.raise_for_status()
        except HTTPError:
            return util.proxy_error(response)

        return HttpResponse(response.content, content_type="application/json")


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
            serializers.SenderSerializer(self.get_object().notifiers.all(), many=True).data
        )


class ServiceViewSet(NotifierMixin, RuleMixin, viewsets.ModelViewSet):
    queryset = models.Service.objects.all()
    filterset_class = filters.ServiceFilter
    serializer_class = serializers.ServiceSerializer
    lookup_value_regex = "[^/]+"
    lookup_field = "name"

    def get_queryset(self):
        query_set = self.queryset
        return query_set.filter(
            pk__in=permissions.get_accessible_services_for_user(self.request.user)
        )

    @action(detail=True, methods=["get"])
    def projects(self, request, name):
        service = self.get_object()
        return Response(serializers.ProjectSerializer(service.project_set.all(), many=True).data)

    @action(detail=True, methods=["get"])
    def targets(self, request, name):
        return HttpResponse(
            prometheus.render_config(service=self.get_object()),
            content_type="application/json",
        )


class ProjectViewSet(NotifierMixin, RuleMixin, viewsets.ModelViewSet):
    queryset = models.Project.objects.prefetch_related("service", "shard", "farm")
    filterset_class = filters.ProjectFilter
    serializer_class = serializers.ProjectSerializer
    lookup_value_regex = "[^/]+"
    lookup_field = "name"

    def get_queryset(self):
        query_set = self.queryset
        return query_set.filter(
            pk__in=permissions.get_accessible_projects_for_user(self.request.user)
        )

    @action(detail=True, methods=["get"])
    def targets(self, request, name):
        return HttpResponse(
            prometheus.render_config(project=self.get_object()),
            content_type="application/json",
        )


class FarmViewSet(viewsets.ModelViewSet):
    queryset = models.Farm.objects.all()
    filterset_class = filters.FarmFilter
    serializer_class = serializers.FarmSerializer
    lookup_value_regex = "[^/]+"
    lookup_field = "id"

    def get_queryset(self):
        query_set = self.queryset
        # If the user is not a superuser, we need to filter the farms by the user's permissions
        if not self.request.user.is_superuser:
            projects = permissions.get_accessible_projects_for_user(self.request.user)
            query_set = query_set.filter(project__in=projects)
        return query_set

    def retrieve(self, request, id):
        farm = self.get_object()
        farm_data = self.get_serializer(farm).data

        hosts = farm.host_set.all()
        hosts_data = serializers.HostSerializer(hosts, many=True).data
        farm_detail = {**farm_data, "hosts": hosts_data}
        return Response(farm_detail)
