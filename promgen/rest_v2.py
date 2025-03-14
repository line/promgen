# Copyright (c) 2026 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.urls import re_path
from drf_spectacular.utils import extend_schema, extend_schema_view
from drf_spectacular.views import SpectacularAPIView
from rest_framework import mixins, pagination, routers, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from promgen import filters, models, permissions, serializers


class SpectacularRapiDocView(APIView):
    renderer_classes = [TemplateHTMLRenderer]
    template_name = "rest_framework/api_v2.html"

    @extend_schema(exclude=True)
    def get(self, request):
        api_token = Token.objects.filter(user=self.request.user).first()
        return Response(
            data={"api_token": api_token},
            template_name=self.template_name,
        )


class Router(routers.DefaultRouter):
    include_root_view = False

    def get_urls(self):
        urls = super().get_urls()

        urls.append(
            re_path(
                rf"^schema{self.trailing_slash}$",
                SpectacularAPIView.as_view(),
                name="schema",
            )
        )

        urls.append(
            re_path(
                rf"^docs{self.trailing_slash}$",
                SpectacularRapiDocView.as_view(),
                name="docs",
            )
        )

        return urls


class PromgenPagination(pagination.PageNumberPagination):
    page_query_param = "page_number"
    page_size_query_param = "page_size"
    page_size = 10
    max_page_size = 1000

    def __init__(self):
        super().__init__()
        self.page_query_description = self.page_query_description + " Starts from 1."
        self.page_size_query_description = self.page_size_query_description + str.format(
            " Defaults to {}.", self.page_size
        )


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
