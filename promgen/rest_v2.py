# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE
from django.contrib.auth.models import User
from drf_spectacular.utils import (
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
