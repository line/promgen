# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE
from http import HTTPStatus

from django.contrib.contenttypes.models import ContentType
from drf_spectacular.utils import (
    extend_schema,
)
from rest_framework import pagination
from rest_framework.decorators import action
from rest_framework.response import Response

from promgen import models, serializers


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
