# Copyright (c) 2026 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
)
from rest_framework import mixins, pagination, viewsets

from promgen import filters, models, permissions, serializers


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
