# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE
from django.contrib.admin.options import get_content_type_for_model
from django.contrib.auth.models import User
from drf_spectacular.utils import (
    OpenApiParameter,
    extend_schema,
    extend_schema_view,
)
from rest_framework import mixins, pagination, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from promgen import filters, models, renderers, serializers

class RuleMixin:
    @extend_schema(
        summary="Retrieve Rules",
        description="Fetch rules associated with the specified object.",
    )
    @action(detail=True, methods=["get"], renderer_classes=[renderers.RuleRenderer])
    def rules(self, request, id):
        rules = models.Rule.objects.filter(obj=self.get_object())
        return Response(
            serializers.AlertRuleSerializer(rules, many=True).data,
            headers={"Content-Disposition": "attachment; filename=%s.rule.yml" % id},
        )


class NotifierMixin:
    @extend_schema(
        summary="List Notifiers",
        description="Retrieve all notifiers associated with the specified object.",
    )
    @action(detail=True, methods=["get"])
    def notifiers(self, request, id):
        return Response(
            serializers.SenderSerializer(self.get_object().notifiers.all(), many=True).data
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
    queryset = User.objects.all()
    filterset_class = filters.UserFilter
    serializer_class = serializers.UserSerializer
    lookup_value_regex = "[^/]+"
    pagination_class = PromgenPagination

    @extend_schema(
        summary="Get Current User",
        description="Retrieve the current authenticated user's information.",
        responses=serializers.CurrentUserSerializer,
    )
    @action(detail=False, methods=["get"], url_path="me")
    def get_current_user(self, request):
        return Response(serializers.CurrentUserSerializer(request.user).data)


@extend_schema_view(
    list=extend_schema(summary="List Audit Logs", description="Retrieve a list of all audit logs."),
)
@extend_schema(tags=["Log"])
class AuditViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = models.Audit.objects.all()
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
    queryset = models.Sender.objects.all()
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
        return None

    @extend_schema(
        summary="Add Filter",
        description="Add a filter to the specified notifier.",
        request=serializers.FilterSerializer,
        responses=serializers.NotifierSerializer,
    )
    @action(detail=True, methods=["post"], url_path="filter-add")
    def add_filter(self, request, id):
        notifier = self.get_object()
        serializer = serializers.FilterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        models.Filter.objects.create(
            sender=notifier,
            name=serializer.validated_data["name"],
            value=serializer.validated_data["value"],
        )
        return Response(serializers.NotifierSerializer(notifier).data)

    @extend_schema(
        summary="Delete Filter",
        description="Delete a filter from the specified notifier.",
        request=serializers.FilterSerializer,
        responses=serializers.NotifierSerializer,
    )
    @action(detail=True, methods=["post"], url_path="filter-delete")
    def delete_filter(self, request, id):
        notifier = self.get_object()
        serializer = serializers.FilterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        models.Filter.objects.filter(
            sender=notifier,
            name=serializer.validated_data["name"],
            value=serializer.validated_data["value"],
        ).delete()
        return Response(serializers.NotifierSerializer(notifier).data)


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
