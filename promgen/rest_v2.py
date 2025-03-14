# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE
from http import HTTPStatus

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from drf_spectacular.utils import (
    OpenApiParameter,
    extend_schema,
    extend_schema_view,
)
from rest_framework import mixins, pagination, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from promgen import filters, models, serializers, signals


class RuleMixin:
    @extend_schema(
        summary="List Rules",
        description="Retrieve all rules associated with the specified object.",
        responses=serializers.RuleSerializer(many=True),
    )
    @action(detail=True, methods=["get"], pagination_class=None, filterset_class=None)
    def rules(self, request, id):
        return Response(
            serializers.RuleSerializer(self.get_object().rule_set.all(), many=True).data
        )

    @extend_schema(
        summary="Register Rule",
        description="Register a new rule for the specified object.",
        request=serializers.RuleSerializer,
        responses={201: serializers.RuleSerializer(many=True)},
    )
    @rules.mapping.post
    def register_rule(self, request, id):
        serializer = serializers.RuleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        object = self.get_object()

        attributes = {
            "content_type_id": ContentType.objects.get_for_model(object).id,
            "object_id": object.id,
        }

        for field in serializer.fields:
            value = serializer.validated_data.get(field)
            if value is not None:
                attributes[field] = value

        rule, _ = models.Rule.objects.get_or_create(**attributes)
        return Response(
            serializers.RuleSerializer(object.rule_set, many=True).data, status=HTTPStatus.CREATED
        )


class NotifierMixin:
    @extend_schema(
        summary="List Notifiers",
        description="Retrieve all notifiers associated with the specified object.",
        responses=serializers.SenderSerializer(many=True),
    )
    @action(detail=True, methods=["get"], pagination_class=None, filterset_class=None)
    def notifiers(self, request, id):
        return Response(
            serializers.SenderSerializer(self.get_object().notifiers.all(), many=True).data
        )

    @extend_schema(
        summary="Register Notifier",
        description="Register a new notifier for the specified object.",
        request=serializers.RegisterNotifierSerializer,
        responses={201: serializers.NotifierSerializer(many=True)},
    )
    @notifiers.mapping.post
    def register_notifier(self, request, id):
        serializer = serializers.RegisterNotifierSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        object = self.get_object()

        attributes = {
            "content_type_id": ContentType.objects.get_for_model(object).id,
            "object_id": object.id,
        }

        for field in serializer.fields:
            value = serializer.validated_data.get(field)
            if value is not None and field != "filters":
                attributes[field] = value

        notifier, _ = models.Sender.objects.get_or_create(**attributes)
        for filter_data in serializer.validated_data.get("filters", []):
            models.Filter.objects.get_or_create(sender=notifier, **filter_data)
        return Response(
            serializers.NotifierSerializer(object.notifiers, many=True).data,
            status=HTTPStatus.CREATED,
        )


class PromgenPagination(pagination.PageNumberPagination):
    page_query_param = "page_number"
    page_size_query_param = "page_size"
    page_size = 100  # Default page size
    max_page_size = 1000


@extend_schema_view(
    list=extend_schema(summary="List Users", description="Retrieve a list of all users."),
)
@extend_schema(tags=["User"])
class UserViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = User.objects.all().order_by("id")
    filterset_class = filters.UserFilter
    serializer_class = serializers.UserSerializer
    lookup_value_regex = "[^/]+"
    pagination_class = PromgenPagination

    @extend_schema(
        summary="Get Current User",
        description="Retrieve the current authenticated user's information.",
        responses=serializers.CurrentUserSerializer,
    )
    @action(detail=False, methods=["get"], url_path="me", permission_classes=[IsAuthenticated])
    def get_current_user(self, request):
        return Response(serializers.CurrentUserSerializer(request.user).data)


@extend_schema_view(
    list=extend_schema(summary="List Audit Logs", description="Retrieve a list of all audit logs."),
)
@extend_schema(tags=["Log"])
class AuditViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = models.Audit.objects.all().order_by("-created")
    filterset_class = filters.AuditFilter
    serializer_class = serializers.AuditSerializer
    lookup_value_regex = "[^/]+"
    lookup_field = "id"
    pagination_class = PromgenPagination


@extend_schema_view(
    list=extend_schema(summary="List Notifiers", description="Retrieve a list of all notifiers."),
    update=extend_schema(summary="Update Notifier", description="Update an existing notifier."),
    partial_update=extend_schema(
        summary="Partially Update Notifier", description="Partially update an existing notifier."
    ),
    destroy=extend_schema(summary="Delete Notifier", description="Delete an existing notifier."),
)
@extend_schema(tags=["Notifier"])
class NotifierViewSet(
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = models.Sender.objects.all().order_by("value")
    filterset_class = filters.NotifierFilter
    lookup_value_regex = "[^/]+"
    lookup_field = "id"
    pagination_class = PromgenPagination

    def get_serializer_class(self):
        if self.action == "list":
            return serializers.NotifierSerializer
        if self.action == "update":
            return serializers.UpdateNotifierSerializer
        if self.action == "partial_update":
            return serializers.UpdateNotifierSerializer
        return serializers.NotifierSerializer

    @extend_schema(
        summary="Add Filter",
        description="Add a filter to the specified notifier.",
        request=serializers.FilterSerializer,
        responses=serializers.NotifierSerializer,
    )
    @action(detail=True, methods=["post"], url_path="filters")
    def add_filter(self, request, id):
        notifier = self.get_object()
        serializer = serializers.FilterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        models.Filter.objects.create(
            sender=notifier,
            name=serializer.validated_data["name"],
            value=serializer.validated_data["value"],
        )
        return Response(serializers.NotifierSerializer(notifier).data, status=HTTPStatus.CREATED)

    @extend_schema(
        summary="Delete Filter",
        description="Delete a filter from the specified notifier.",
    )
    @action(detail=True, methods=["delete"], url_path="filters/(?P<filter_id>\d+)")
    def delete_filter(self, request, id, filter_id):
        notifier = self.get_object()
        if notifier:
            models.Filter.objects.filter(pk=filter_id).delete()
        return Response(status=HTTPStatus.NO_CONTENT)


@extend_schema_view(
    list=extend_schema(summary="List Rules", description="Retrieve a list of all rules."),
    retrieve=extend_schema(
        summary="Retrieve Rule", description="Retrieve detailed information about a specific rule."
    ),
    update=extend_schema(summary="Update Rule", description="Update an existing rule."),
    partial_update=extend_schema(
        summary="Partially Update Rule", description="Partially update an existing rule."
    ),
    destroy=extend_schema(summary="Delete Rule", description="Delete an existing rule."),
)
@extend_schema(tags=["Rule"])
class RuleViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = models.Rule.objects.all()
    filterset_class = filters.RuleFilterV2
    serializer_class = serializers.RuleSerializer
    lookup_value_regex = "[^/]+"
    lookup_field = "id"
    pagination_class = PromgenPagination


@extend_schema_view(
    list=extend_schema(summary="List Farms", description="Retrieve a list of all farms."),
    retrieve=extend_schema(
        summary="Retrieve Farm", description="Retrieve detailed information about a specific farm."
    ),
    create=extend_schema(summary="Create Farm", description="Create a new farm."),
    update=extend_schema(summary="Update Farm", description="Update an existing farm."),
    partial_update=extend_schema(
        summary="Partially Update Farm", description="Partially update an existing farm."
    ),
    destroy=extend_schema(summary="Delete Farm", description="Delete an existing farm."),
)
@extend_schema(tags=["Farm"])
class FarmViewSet(viewsets.ModelViewSet):
    queryset = models.Farm.objects.all()
    filterset_class = filters.FarmFilter
    serializer_class = serializers.FarmRetrieveSerializer
    lookup_value_regex = "[^/]+"
    lookup_field = "id"
    pagination_class = PromgenPagination

    def get_serializer_class(self):
        if self.action == "list":
            return serializers.FarmRetrieveSerializer
        if self.action == "retrieve":
            return serializers.FarmRetrieveSerializer
        if self.action == "create":
            return serializers.FarmRetrieveSerializer
        if self.action == "update":
            return serializers.FarmUpdateSerializer
        if self.action == "partial_update":
            return serializers.FarmUpdateSerializer
        return serializers.FarmRetrieveSerializer

    @extend_schema(
        summary="List Hosts in Farm",
        description="Retrieve all hosts associated with the specified farm.",
        parameters=[
            OpenApiParameter(name="page_number", required=False, type=int),
            OpenApiParameter(name="page_size", required=False, type=int),
        ],
        responses=serializers.HostRetrieveSerializer(many=True),
    )
    @action(detail=True, methods=["get"], filterset_class=None)
    def hosts(self, request, id):
        farm = self.get_object()
        hosts = farm.host_set.all()
        page = self.paginate_queryset(hosts)
        return self.get_paginated_response(serializers.HostRetrieveSerializer(page, many=True).data)

    @extend_schema(
        summary="List Projects in Farm",
        description="Retrieve all projects associated with the specified farm.",
        parameters=[
            OpenApiParameter(name="page_number", required=False, type=int),
            OpenApiParameter(name="page_size", required=False, type=int),
        ],
        responses=serializers.ProjectV2Serializer(many=True),
    )
    @action(detail=True, methods=["get"], filterset_class=None)
    def projects(self, request, id):
        farm = self.get_object()
        projects = farm.project_set.all()
        page = self.paginate_queryset(projects)
        return self.get_paginated_response(serializers.ProjectV2Serializer(page, many=True).data)

    @extend_schema(
        summary="Register Hosts",
        description="Register new hosts for the specified farm.",
        request=serializers.HostListSerializer,
        responses={201: None},
    )
    @hosts.mapping.post
    def register_host(self, request, id):
        farm = self.get_object()
        hostnames = request.data.get("hosts", [])
        for hostname in hostnames:
            models.Host.objects.get_or_create(name=hostname, farm_id=farm.id)
        return Response(status=HTTPStatus.CREATED)

    @extend_schema(
        summary="Delete Hosts",
        description="Delete hosts from the specified farm.",
    )
    @action(
        detail=True, methods=["delete"], url_path="hosts/(?P<host_id>\d+)", pagination_class=None
    )
    def delete_host(self, request, id, host_id):
        farm = self.get_object()
        models.Host.objects.filter(pk=host_id, farm=farm).delete()
        return Response(status=HTTPStatus.NO_CONTENT)


@extend_schema_view(
    list=extend_schema(summary="List Exporters", description="Retrieve a list of all exporters."),
    retrieve=extend_schema(
        summary="Retrieve Exporter",
        description="Retrieve detailed information about a specific exporter.",
    ),
)
@extend_schema(tags=["Exporter"])
class ExporterViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = models.Exporter.objects.all()
    filterset_class = filters.ExporterFilter
    serializer_class = serializers.ExporterSerializer
    lookup_value_regex = "[^/]+"
    lookup_field = "id"
    pagination_class = PromgenPagination


@extend_schema_view(
    list=extend_schema(summary="List URLs", description="Retrieve a list of all URLs."),
    retrieve=extend_schema(
        summary="Retrieve URL", description="Retrieve detailed information about a specific URL."
    ),
)
@extend_schema(tags=["URL"])
class URLViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = models.URL.objects.all()
    filterset_class = filters.URLFilter
    serializer_class = serializers.URLSerializer
    lookup_value_regex = "[^/]+"
    lookup_field = "id"
    pagination_class = PromgenPagination


@extend_schema_view(
    list=extend_schema(summary="List Projects", description="Retrieve a list of all projects."),
    retrieve=extend_schema(
        summary="Retrieve Project",
        description="Retrieve detailed information about a specific project.",
    ),
    create=extend_schema(summary="Create Project", description="Create a new project."),
    update=extend_schema(summary="Update Project", description="Update an existing project."),
    partial_update=extend_schema(
        summary="Partially Update Project", description="Partially update an existing project."
    ),
    destroy=extend_schema(summary="Delete Project", description="Delete an existing project."),
)
@extend_schema(tags=["Project"])
class ProjectViewSet(NotifierMixin, RuleMixin, viewsets.ModelViewSet):
    queryset = models.Project.objects.prefetch_related("service", "shard", "farm")
    filterset_class = filters.ProjectFilterV2
    lookup_value_regex = "[^/]+"
    lookup_field = "id"
    pagination_class = PromgenPagination

    def get_serializer_class(self):
        if self.action == "list":
            return serializers.ProjectV2Serializer
        if self.action == "retrieve":
            return serializers.ProjectV2Serializer
        if self.action == "create":
            return serializers.ProjectV2Serializer
        if self.action == "update":
            return serializers.ProjectUpdateSerializer
        if self.action == "partial_update":
            return serializers.ProjectUpdateSerializer
        return serializers.ProjectV2Serializer

    @extend_schema(
        summary="List Exporters",
        description="Retrieve all exporters associated with the specified project.",
        responses=serializers.ExporterSerializer(many=True),
    )
    @action(detail=True, methods=["get"], pagination_class=None, filterset_class=None)
    def exporters(self, request, id):
        project = self.get_object()
        return Response(serializers.ExporterSerializer(project.exporter_set.all(), many=True).data)

    @extend_schema(
        summary="List URLs",
        description="Retrieve all URLs associated with the specified project.",
        responses=serializers.URLSerializer(many=True),
    )
    @action(detail=True, methods=["get"], pagination_class=None, filterset_class=None)
    def urls(self, request, id):
        project = self.get_object()
        return Response(serializers.URLSerializer(project.url_set.all(), many=True).data)

    @extend_schema(
        summary="Link Farm",
        description="Link a farm to the specified project.",
        request=serializers.LinkFarmSerializer,
        responses=serializers.ProjectV2Serializer,
    )
    @action(detail=True, methods=["patch"], url_path="farm-link")
    def link_farm(self, request, id):
        serializer = serializers.LinkFarmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = self.get_object()
        farm, created = models.Farm.objects.get_or_create(
            name=serializer.validated_data["farm"],
            source=serializer.validated_data["source"],
        )
        if created:
            farm.refresh()
        project.farm = farm
        project.save()
        return Response(serializers.ProjectV2Serializer(project).data)

    @extend_schema(
        summary="Unlink Farm",
        description="Unlink the farm from the specified project.",
        responses=serializers.ProjectV2Serializer,
    )
    @action(detail=True, methods=["patch"], url_path="farm-unlink")
    def unlink_farm(self, request, id):
        project = self.get_object()
        if project.farm is None:
            return Response(serializers.ProjectV2Serializer(project).data)

        old_farm, project.farm = project.farm, None
        project.save()
        signals.trigger_write_config.send(request)

        if old_farm.project_set.count() == 0 and old_farm.editable is False:
            old_farm.delete()
        return Response(serializers.ProjectV2Serializer(project).data)

    @extend_schema(
        summary="Register URL",
        description="Register a new URL for the specified project.",
        request=serializers.RegisterURLProjectSerializer,
        responses={201: serializers.URLSerializer(many=True)},
    )
    @urls.mapping.post
    def register_url(self, request, id):
        serializer = serializers.RegisterURLProjectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = self.get_object()

        models.URL.objects.get_or_create(
            project=project,
            url=serializer.validated_data["url"],
            probe=serializer.validated_data["probe"],
        )
        return Response(
            serializers.URLSerializer(project.url_set, many=True).data, status=HTTPStatus.CREATED
        )

    @extend_schema(
        summary="Delete URL",
        description="Delete a URL from the specified project.",
    )
    @action(
        detail=True,
        methods=["delete"],
        url_path="urls/(?P<url_id>\d+)",
        pagination_class=None,
        filterset_class=None,
    )
    def delete_url(self, request, id, url_id):
        project = self.get_object()
        models.URL.objects.filter(project=project, pk=url_id).delete()
        return Response(status=HTTPStatus.NO_CONTENT)

    @extend_schema(
        summary="Register Exporter",
        description="Register a new exporter for the specified project.",
        request=serializers.RegisterExporterProjectSerializer,
        responses={201: serializers.ExporterSerializer(many=True)},
    )
    @exporters.mapping.post
    def register_exporter(self, request, id):
        serializer = serializers.RegisterExporterProjectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = self.get_object()

        attributes = {
            "project_id": project.id,
        }

        for field in serializer.fields:
            value = serializer.validated_data.get(field)
            if value is not None:
                attributes[field] = value

        models.Exporter.objects.get_or_create(**attributes)
        return Response(
            serializers.ExporterSerializer(project.exporter_set, many=True).data,
            status=HTTPStatus.CREATED,
        )

    @extend_schema(
        summary="Update Exporter",
        description="Update an existing exporter for the specified project.",
        request=serializers.UpdateExporterProjectSerializer,
        responses=serializers.ExporterSerializer(many=True),
    )
    @action(
        detail=True,
        methods=["patch"],
        url_path="exporters/(?P<exporter_id>\d+)",
        pagination_class=None,
        filterset_class=None,
    )
    def update_exporter(self, request, id, exporter_id):
        serializer = serializers.UpdateExporterProjectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = self.get_object()
        exporter = models.Exporter.objects.filter(project=project, pk=exporter_id).first()
        exporter.enabled = serializer.validated_data.get("enabled")
        exporter.save()
        return Response(serializers.ExporterSerializer(project.exporter_set, many=True).data)

    @extend_schema(
        summary="Delete Exporter",
        description="Delete an exporter from the specified project.",
    )
    @update_exporter.mapping.delete
    def delete_exporter(self, request, id, exporter_id):
        project = self.get_object()
        models.Exporter.objects.filter(project=project, pk=exporter_id).delete()
        return Response(status=HTTPStatus.NO_CONTENT)


@extend_schema_view(
    list=extend_schema(
        summary="List Services",
        description="Retrieve a list of all services.",
    ),
    retrieve=extend_schema(
        summary="Retrieve Service",
        description="Retrieve detailed information about a specific service.",
    ),
    create=extend_schema(summary="Create Service", description="Create a new service."),
    update=extend_schema(summary="Update Service", description="Update an existing service."),
    partial_update=extend_schema(
        summary="Partially Update Service", description="Partially update an existing service."
    ),
    destroy=extend_schema(summary="Delete Service", description="Delete an existing service."),
)
@extend_schema(tags=["Service"])
class ServiceViewSet(NotifierMixin, RuleMixin, viewsets.ModelViewSet):
    model = "Service"
    queryset = models.Service.objects.all()
    filterset_class = filters.ServiceFilterV2
    serializer_class = serializers.ServiceSerializer
    lookup_value_regex = "[^/]+"
    lookup_field = "id"
    pagination_class = PromgenPagination

    def get_serializer_class(self):
        if self.action == "list":
            return serializers.ServiceV2Serializer
        if self.action == "retrieve":
            return serializers.ServiceV2Serializer
        if self.action == "create":
            return serializers.ServiceV2Serializer
        if self.action == "update":
            return serializers.ServiceUpdateSerializer
        if self.action == "partial_update":
            return serializers.ServiceUpdateSerializer
        return serializers.ServiceV2Serializer

    @extend_schema(
        summary="List Projects",
        description="Retrieve all projects associated with the specified service.",
        responses=serializers.ProjectV2Serializer(many=True),
    )
    @action(detail=True, methods=["get"], pagination_class=None, filterset_class=None)
    def projects(self, request, id):
        service = self.get_object()
        return Response(serializers.ProjectV2Serializer(service.project_set.all(), many=True).data)

    @extend_schema(
        summary="Register Project",
        description="Register a new project for the specified service.",
        request=serializers.ProjectUpdateSerializer,
        responses={201: serializers.ProjectV2Serializer},
    )
    @projects.mapping.post
    def register_project(self, request, id):
        serializer = serializers.ProjectUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = self.get_object()

        attributes = {"service": service}

        for field in serializer.fields:
            value = serializer.validated_data.get(field)
            if value is not None:
                attributes[field] = value

        project, _ = models.Project.objects.get_or_create(**attributes)
        return Response(serializers.ProjectV2Serializer(project).data, status=HTTPStatus.CREATED)
