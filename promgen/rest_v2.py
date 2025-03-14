# Copyright (c) 2026 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE
from http import HTTPStatus

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from drf_spectacular.utils import (
    OpenApiParameter,
    extend_schema,
    extend_schema_view,
)
from rest_framework import mixins, pagination, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from promgen import discovery, filters, models, permissions, serializers, signals, validators


class PromgenPagination(pagination.PageNumberPagination):
    page_query_param = "page_number"
    page_size_query_param = "page_size"
    page_size = 100  # Default page size
    max_page_size = 1000


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
    permission_classes = [permissions.PromgenGuardianRestPermission]

    def get_queryset(self):
        if self.request.user.is_superuser or self.action != "list":
            return self.queryset
        services = permissions.get_accessible_services_for_user(self.request.user)
        projects = permissions.get_accessible_projects_for_user(self.request.user)
        farms = models.Farm.objects.filter(project__in=projects)
        groups = permissions.get_accessible_groups_for_user(self.request.user)
        service_ct = ContentType.objects.get_for_model(models.Service)
        project_ct = ContentType.objects.get_for_model(models.Project)
        farm_ct = ContentType.objects.get_for_model(models.Farm)
        group_ct = ContentType.objects.get_for_model(models.Group)
        return self.queryset.filter(
            Q(
                content_type__model="service",
                content_type__app_label="promgen",
                object_id__in=services,
            )
            | Q(
                content_type__model="project",
                content_type__app_label="promgen",
                object_id__in=projects,
            )
            | Q(content_type__model="farm", content_type__app_label="promgen", object_id__in=farms)
            | Q(parent_content_type_id=service_ct.id, parent_object_id__in=services)
            | Q(parent_content_type_id=project_ct.id, parent_object_id__in=projects)
            | Q(parent_content_type_id=farm_ct.id, parent_object_id__in=farms)
            | Q(content_type__model="group", content_type__app_label="auth", object_id__in=groups)
            | Q(parent_content_type_id=group_ct.id, parent_object_id__in=groups)
        )


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
    permission_classes = [permissions.PromgenGuardianRestPermission]

    def get_queryset(self):
        if self.request.user.is_superuser or self.action != "list":
            return self.queryset
        accessible_projects = permissions.get_accessible_projects_for_user(self.request.user)
        accessible_services = permissions.get_accessible_services_for_user(self.request.user)
        project_ct = ContentType.objects.get_for_model(models.Project)
        service_ct = ContentType.objects.get_for_model(models.Service)
        user_ct = ContentType.objects.get_for_model(User)
        return self.queryset.filter(
            Q(content_type=project_ct, object_id__in=accessible_projects)
            | Q(content_type=service_ct, object_id__in=accessible_services)
            | Q(content_type=user_ct, object_id=self.request.user.id)
        )

    def get_serializer_class(self):
        if self.action in ["update", "partial_update"]:
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
    permission_classes = [permissions.PromgenGuardianRestPermission]

    def get_queryset(self):
        if self.request.user.is_superuser or self.action != "list":
            return self.queryset
        accessible_projects = permissions.get_accessible_projects_for_user(self.request.user)
        accessible_services = permissions.get_accessible_services_for_user(self.request.user)
        project_ct = ContentType.objects.get_for_model(models.Project)
        service_ct = ContentType.objects.get_for_model(models.Service)
        site_ct = ContentType.objects.get_for_model(models.Site, for_concrete_model=False)
        return self.queryset.filter(
            Q(content_type=project_ct, object_id__in=accessible_projects)
            | Q(content_type=service_ct, object_id__in=accessible_services)
            | Q(content_type=site_ct)
        )


@extend_schema_view(
    list=extend_schema(
        summary="List Created Farms", description="Retrieve a list of all created farms."
    ),
    retrieve=extend_schema(
        summary="Retrieve Farm", description="Retrieve detailed information about a specific farm."
    ),
    update=extend_schema(summary="Update Farm", description="Update an existing farm."),
    partial_update=extend_schema(
        summary="Partially Update Farm", description="Partially update an existing farm."
    ),
    destroy=extend_schema(summary="Delete Farm", description="Delete an existing farm."),
)
@extend_schema(tags=["Farm"])
class FarmViewSet(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = models.Farm.objects.all()
    filterset_class = filters.FarmFilter
    serializer_class = serializers.FarmRetrieveSerializer
    lookup_value_regex = "[^/]+"
    lookup_field = "id"
    pagination_class = PromgenPagination
    permission_classes = [permissions.PromgenGuardianRestPermission]

    def get_queryset(self):
        if self.request.user.is_superuser or self.action != "list":
            return self.queryset
        accessible_projects = permissions.get_accessible_projects_for_user(self.request.user)
        return self.queryset.filter(project__in=accessible_projects)

    def get_serializer_class(self):
        if self.action in ["update", "partial_update"]:
            return serializers.FarmUpdateSerializer
        return serializers.FarmRetrieveSerializer

    def update(self, request, *args, **kwargs):
        farm = self.get_object()
        if farm.source != discovery.FARM_DEFAULT:
            raise ValidationError({"detail": "Only local farms can be updated."})
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        farm = self.get_object()
        if farm.source != discovery.FARM_DEFAULT:
            raise ValidationError({"detail": "Only local farms can be updated."})
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        farm = self.get_object()
        if farm.source != discovery.FARM_DEFAULT:
            raise ValidationError({"detail": "Only local farms can be deleted."})
        return super().destroy(request, *args, **kwargs)

    @extend_schema(
        summary="List Farm Sources",
        description="Retrieve available farm sources and whether they are remote.",
        responses=serializers.FarmSourceSerializer(many=True),
    )
    @action(detail=False, methods=["get"], pagination_class=None, filterset_class=None)
    def sources(self, request):
        source_data = sorted(
            [{"name": name, "remote": driver.remote} for name, driver in models.Farm.driver_set()],
            key=lambda source: source["name"],
        )
        return Response(serializers.FarmSourceSerializer(source_data, many=True).data)

    @extend_schema(
        summary="List Remote Farms by Source",
        description="Retrieve remote farm names from the specified remote source.",
        responses=serializers.RemoteFarmSerializer(many=True),
    )
    @action(
        detail=False,
        methods=["get"],
        url_path=r"remotes/(?P<source>[^/]+)",
        pagination_class=None,
        filterset_class=None,
    )
    def remote(self, request, source):
        driver = None
        for driver_name, farm_driver in models.Farm.driver_set():
            if driver_name == source:
                driver = farm_driver
                break

        if driver is None:
            raise ValidationError({"source": "Unknown farm source."})
        if not driver.remote:
            raise ValidationError({"source": "Only remote farm sources are supported."})

        remote_farms = sorted(set(models.Farm.fetch(source)))
        farm_data = [{"name": farm_name} for farm_name in remote_farms]
        return Response(serializers.RemoteFarmSerializer(farm_data, many=True).data)

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
        summary="Register Hosts",
        description="Register new hosts for the specified farm.",
        request=serializers.HostListSerializer,
        responses={201: serializers.HostListSerializer},
    )
    @hosts.mapping.post
    def register_host(self, request, id):
        farm = self.get_object()
        hostnames = request.data.get("hosts", [])
        valid_hosts = set()
        for hostname in hostnames:
            if hostname == "":
                continue
            validators.hostname(hostname)
            valid_hosts.add(hostname)

        for valid_host in valid_hosts:
            models.Host.objects.get_or_create(name=valid_host, farm_id=farm.id)
        return Response(
            serializers.HostListSerializer({"hosts": sorted(valid_hosts)}).data,
            status=HTTPStatus.CREATED,
        )

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

    @extend_schema(
        summary="Sync Farm",
        description="Refresh hosts from the farm source.",
        responses=serializers.FarmRetrieveSerializer,
    )
    @action(detail=True, methods=["post"], pagination_class=None, filterset_class=None)
    def sync(self, request, id):
        farm = self.get_object()
        if farm.source == discovery.FARM_DEFAULT:
            raise ValidationError({"detail": "Only remote farms can be synced."})
        # If any hosts are added or removed, then we want to trigger a config refresh
        if any(farm.refresh()):
            signals.trigger_write_config.send(request)
        return Response(serializers.FarmRetrieveSerializer(farm).data)

    @extend_schema(
        summary="Convert to Local Farm",
        description="Convert a remote farm to a local promgen farm source.",
        responses=serializers.FarmRetrieveSerializer,
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="convert-to-local",
        pagination_class=None,
        filterset_class=None,
    )
    def convert_to_local_farm(self, request, id):
        farm = self.get_object()
        if farm.source == discovery.FARM_DEFAULT:
            raise ValidationError({"detail": "Only remote farms can be converted to local."})
        farm.source = discovery.FARM_DEFAULT
        farm.save()
        return Response(serializers.FarmRetrieveSerializer(farm).data)
