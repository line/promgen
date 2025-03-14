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

from promgen import filters, models, serializers


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
