# Copyright (c) 2026 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE
from http import HTTPStatus

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.urls import re_path
from drf_spectacular.utils import (
    OpenApiParameter,
    extend_schema,
    extend_schema_view,
)
from drf_spectacular.views import SpectacularAPIView
from guardian.models import GroupObjectPermission
from guardian.shortcuts import assign_perm, get_perms, remove_perm
from rest_framework import mixins, pagination, routers, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed, ValidationError
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from promgen import discovery, filters, models, permissions, serializers, signals, validators
from promgen.templatetags import promgen as shortcuts


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
        groups = permissions.get_accessible_groups_for_user(self.request.user)
        service_ct = ContentType.objects.get_for_model(models.Service)
        project_ct = ContentType.objects.get_for_model(models.Project)
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
            | Q(
                content_type__model="group",
                content_type__app_label="auth",
                object_id__in=groups,
            )
            | Q(parent_content_type_id=service_ct.id, parent_object_id__in=services)
            | Q(parent_content_type_id=project_ct.id, parent_object_id__in=projects)
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
    lookup_value_regex = "[^/]+"
    lookup_field = "id"
    pagination_class = PromgenPagination
    permission_classes = [permissions.PromgenGuardianRestPermission]

    def get_serializer_class(self):
        if self.action in ["list"]:
            return serializers.RuleRetrieveSimpleSerializer
        return serializers.RuleRetrieveDetailSerializer

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

    @extend_schema(
        summary="List Farm Sources",
        description="Retrieve available farm sources and whether they are remote.",
        parameters=[
            OpenApiParameter(
                name="name",
                required=False,
                type=str,
                description="Filter by source name containing a specific substring. "
                "Example: name=Example Source",
            ),
            OpenApiParameter(
                name="remote",
                required=False,
                type=bool,
                description="Filter by whether the source is remote. Example: remote=true",
            ),
        ],
        responses=serializers.FarmSourceSerializer(many=True),
    )
    @action(detail=False, methods=["get"], filterset_class=None)
    def sources(self, request):
        source_data = sorted(
            [{"name": name, "remote": driver.remote} for name, driver in models.Farm.driver_set()],
            key=lambda source: source["name"].lower(),
        )

        name = request.query_params.get("name")
        if name:
            source_data = [
                source for source in source_data if name.lower() in source["name"].lower()
            ]

        remote = request.query_params.get("remote")
        if remote is not None:
            if remote.lower() == "true":
                remote_bool = True
            elif remote.lower() == "false":
                remote_bool = False
            else:
                raise ValidationError({"detail": "Invalid value for remote. Use true or false."})
            source_data = [source for source in source_data if source["remote"] == remote_bool]

        page = self.paginate_queryset(source_data)
        return self.get_paginated_response(serializers.FarmSourceSerializer(page, many=True).data)

    @extend_schema(
        summary="List Remote Farms by Source",
        description="Retrieve remote farm names from the specified remote source.",
        parameters=[
            OpenApiParameter(
                name="name",
                required=False,
                type=str,
                description="Filter by farm name containing a specific substring. "
                "Example: name=Example Farm",
            )
        ],
        responses=serializers.RemoteFarmSerializer(many=True),
    )
    @action(
        detail=False,
        methods=["get"],
        url_path=r"remotes/(?P<source>[^/]+)",
        filterset_class=None,
    )
    def remote(self, request, source):
        driver = None
        for driver_name, farm_driver in models.Farm.driver_set():
            if driver_name == source:
                driver = farm_driver
                break

        if driver is None:
            raise ValidationError({"detail": "Unknown farm source."})
        if not driver.remote:
            raise ValidationError({"detail": "Only remote farm sources are supported."})

        name = request.query_params.get("name")
        remote_farms = set(models.Farm.fetch(source))
        if name:
            remote_farms = [farm_name for farm_name in remote_farms if name in farm_name]

        farm_data = sorted(
            ({"name": farm_name} for farm_name in remote_farms),
            key=lambda item: item["name"].lower(),
        )
        page = self.paginate_queryset(farm_data)
        return self.get_paginated_response(serializers.RemoteFarmSerializer(page, many=True).data)

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
        description="Register new hosts for the specified farm. "
        "Hosts are only registered if all of the provided hostnames are valid.",
        request=serializers.HostListSerializer,
        responses={204: None},
    )
    @hosts.mapping.post
    def register_host(self, request, id):
        farm = self.get_object()
        hostnames = request.data.get("hosts", [])
        valid_hosts = set()
        invalid_hosts = set()
        for hostname in hostnames:
            if hostname == "":
                continue
            try:
                validators.hostname(hostname)
            except DjangoValidationError:
                invalid_hosts.add(hostname)
            valid_hosts.add(hostname)

        if invalid_hosts:
            raise ValidationError(
                {"detail": "Invalid hostnames.", "extras": {"invalid_hosts": list(invalid_hosts)}}
            )

        for valid_host in valid_hosts:
            models.Host.objects.get_or_create(name=valid_host, farm_id=farm.id)
        return Response(status=HTTPStatus.NO_CONTENT)

    @extend_schema(exclude=True)
    @action(detail=True, methods=["get"], url_path="hosts/(?P<host_id>\d+)", pagination_class=None)
    def host(self, request, id, host_id):
        raise MethodNotAllowed(request.method)

    @extend_schema(
        summary="Delete Hosts",
        description="Delete hosts from the specified farm.",
    )
    @host.mapping.delete
    def delete_host(self, request, id, host_id):
        farm = self.get_object()
        models.Host.objects.filter(pk=host_id, farm=farm).delete()
        return Response(status=HTTPStatus.NO_CONTENT)

    @extend_schema(
        summary="Sync Farm",
        description="Refresh hosts from the farm source.",
        request=None,
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
        description="Convert a remote farm to a local Promgen farm source.",
        request=None,
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


@extend_schema_view(
    list=extend_schema(summary="List Exporters", description="Retrieve a list of all exporters."),
    retrieve=extend_schema(
        summary="Retrieve Exporter",
        description="Retrieve detailed information about a specific exporter.",
    ),
    update=extend_schema(summary="Update Exporter", description="Update an existing exporter."),
    partial_update=extend_schema(
        summary="Partially Update Exporter", description="Partially update an existing exporter."
    ),
    destroy=extend_schema(summary="Delete Exporter", description="Delete an existing exporter."),
)
@extend_schema(tags=["Exporter"])
class ExporterViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = models.Exporter.objects.all()
    filterset_class = filters.ExporterFilter
    serializer_class = serializers.ExporterRetrieveSerializer
    lookup_value_regex = "[^/]+"
    lookup_field = "id"
    pagination_class = PromgenPagination
    permission_classes = [permissions.PromgenGuardianRestPermission]

    def get_queryset(self):
        if self.request.user.is_superuser or self.action != "list":
            return self.queryset
        accessible_projects = permissions.get_accessible_projects_for_user(self.request.user)
        return self.queryset.filter(project__in=accessible_projects)


@extend_schema_view(
    list=extend_schema(summary="List URLs", description="Retrieve a list of all URLs."),
    destroy=extend_schema(summary="Delete URL", description="Delete an existing URL."),
)
@extend_schema(tags=["URL"])
class URLViewSet(mixins.ListModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    queryset = models.URL.objects.all()
    filterset_class = filters.URLFilter
    serializer_class = serializers.URLSerializer
    lookup_value_regex = "[^/]+"
    lookup_field = "id"
    pagination_class = PromgenPagination
    permission_classes = [permissions.PromgenGuardianRestPermission]

    def get_queryset(self):
        if self.request.user.is_superuser or self.action != "list":
            return self.queryset
        accessible_projects = permissions.get_accessible_projects_for_user(self.request.user)
        return self.queryset.filter(project__in=accessible_projects)


@extend_schema_view(
    list=extend_schema(summary="List Probes", description="Retrieve a list of all Probes."),
)
@extend_schema(tags=["URL"])
class ProbeViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = models.Probe.objects.all()
    filterset_class = filters.ProbeFilter
    serializer_class = serializers.ProbeSerializer
    lookup_value_regex = "[^/]+"
    pagination_class = PromgenPagination
    permission_classes = [permissions.ReadOnlyForAuthenticatedUserOrIsSuperuser]


@extend_schema_view(
    list=extend_schema(summary="List Groups", description="Retrieve a list of all groups."),
    retrieve=extend_schema(
        summary="Retrieve Group",
        description="Retrieve detailed information about a specific group.",
    ),
    create=extend_schema(summary="Create Group", description="Create a new group."),
    update=extend_schema(summary="Update Group", description="Update an existing group."),
    partial_update=extend_schema(
        summary="Partially Update Group", description="Partially update an existing group."
    ),
    destroy=extend_schema(summary="Delete Group", description="Delete an existing group."),
)
@extend_schema(tags=["Group"])
class GroupViewSet(viewsets.ModelViewSet):
    queryset = models.Group.objects.all()
    filterset_class = filters.GroupFilter
    serializer_class = serializers.GroupRetrieveSerializer
    lookup_value_regex = "[^/]+"
    lookup_field = "id"
    pagination_class = PromgenPagination
    permission_classes = [permissions.PromgenGuardianRestPermission]

    def get_queryset(self):
        if self.request.user.is_superuser or self.action != "list":
            return self.queryset
        return permissions.get_accessible_groups_for_user(self.request.user)

    @extend_schema(
        summary="List Members",
        description="Retrieve a list of all members in the specific group.",
        responses=serializers.UserWithPermRetrieveSerializer(many=True),
    )
    @action(detail=True, methods=["get"], url_path="members")
    def members(self, request, id):
        group = self.get_object()

        users_with_perm = shortcuts.get_users_roles(group)
        members = []
        for user, perm in users_with_perm:
            members.append(
                {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": perm[0].upper(),
                }
            )

        page = self.paginate_queryset(members)
        return self.get_paginated_response(
            serializers.UserWithPermRetrieveSerializer(page, many=True).data
        )

    @extend_schema(
        summary="Add Members",
        description="Add list of members to the group.",
        request=serializers.AddMemberGroupSerializer,
        responses={204: None},
    )
    @members.mapping.post
    def add_members(self, request, id):
        group = self.get_object()
        serializer = serializers.AddMemberGroupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        already_members = User.objects.filter(
            Q(id__in=serializer.validated_data["user_ids"])
            & Q(id__in=group.user_set.values_list("id", flat=True))
        )
        new_members = User.objects.filter(id__in=serializer.validated_data["user_ids"]).exclude(
            id__in=group.user_set.values_list("id", flat=True)
        )

        if already_members.exists():
            raise ValidationError(
                {
                    "detail": "Users are already members of Group {group}: {users}".format(
                        group=group.name,
                        users=[user.username for user in already_members],
                    )
                }
            )

        if new_members.exists():
            content_type = ContentType.objects.get_for_model(group)
            permission = content_type.model + "_" + serializer.validated_data["group_role"].lower()
            for user in new_members:
                group.user_set.add(user)
                assign_perm(permission, user, group)

        return Response(status=HTTPStatus.NO_CONTENT)

    @extend_schema(exclude=True)
    @action(
        detail=True,
        methods=["get"],
        url_path=r"members/(?P<user_id>\d+)",
        pagination_class=None,
        filterset_class=None,
    )
    def member(self, request, id, user_id):
        raise MethodNotAllowed(request.method)

    @extend_schema(
        summary="Update Member",
        description="Change role of a member in the group.",
        request=serializers.UpdateMemberGroupSerializer,
        responses={204: None},
    )
    @member.mapping.put
    def update_member(self, request, id, user_id):
        group = self.get_object()
        user = User.objects.get(id=user_id)
        serializer = serializers.UpdateMemberGroupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if group.user_set.filter(pk=user.pk).exists():
            content_type = ContentType.objects.get_for_model(group)
            permission = content_type.model + "_" + serializer.validated_data["group_role"].lower()
            assign_perm(permission, user, group)
        else:
            raise ValidationError({"detail": f"User {user.id} is not a member of the group"})

        return Response(status=HTTPStatus.NO_CONTENT)

    @extend_schema(
        summary="Remove Member",
        description="Remove a member from the group.",
        responses={204: None},
    )
    @member.mapping.delete
    def remove_member(self, request, id, user_id):
        group = self.get_object()
        user = User.objects.get(id=user_id)

        if group.user_set.filter(pk=user.pk).exists():
            permissions = get_perms(user, group)
            for perm in permissions:
                remove_perm(perm, user, group)
            group.user_set.remove(user)
        else:
            raise ValidationError({"detail": f"User {user.id} is not a member of the group."})

        return Response(status=HTTPStatus.NO_CONTENT)

    @extend_schema(
        summary="List Assigned Resources",
        description="Retrieve a list of all resources assigned with the specific group.",
        responses=serializers.GroupAssignedResourceSerializer(many=True),
    )
    @action(detail=True, methods=["get"], url_path="resources")
    def resources(self, request, id):
        group = self.get_object()

        resources = GroupObjectPermission.objects.filter(group=group)
        assigned_resources = []
        for resource in resources:
            assigned_resources.append(
                {
                    "content_type": resource.content_type.model,
                    "object_id": resource.content_object.id,
                    "name": resource.content_object.name,
                    "role": resource.permission.codename.split("_")[1].upper(),
                }
            )

        page = self.paginate_queryset(assigned_resources)
        return self.get_paginated_response(
            serializers.GroupAssignedResourceSerializer(page, many=True).data
        )
