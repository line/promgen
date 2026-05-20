# Copyright (c) 2026 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

from django.urls import re_path
from drf_spectacular.utils import (
    extend_schema,
)
from drf_spectacular.views import SpectacularAPIView
from rest_framework import pagination, routers
from rest_framework.authtoken.models import Token
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.response import Response
from rest_framework.views import APIView


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
