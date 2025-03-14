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
from guardian.conf.settings import ANONYMOUS_USER_NAME
from guardian.shortcuts import assign_perm, get_perms, remove_perm
from rest_framework import mixins, pagination, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

import promgen.templatetags.promgen as promgen_templatetags
from promgen import discovery, filters, models, permissions, serializers, signals, validators


class PromgenPagination(pagination.PageNumberPagination):
    page_query_param = "page_number"
    page_size_query_param = "page_size"
    page_size = 100  # Default page size
    max_page_size = 1000


class RuleMixin:
    @extend_schema(
        summary="Register Rule",
        description="Register a new rule for the specified object.",
        request=serializers.RuleSerializer,
        responses={201: serializers.RuleSerializer},
    )
    @action(detail=True, methods=["post"], url_path="rules")
    def register_rule(self, request, id):
        object = self.get_object()
        serializer = serializers.RuleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        attributes = {
            "content_type_id": ContentType.objects.get_for_model(object).id,
            "object_id": object.id,
        }

        for field in serializer.fields:
            value = serializer.validated_data.get(field)
            if value is not None:
                attributes[field] = value

        rule, created = models.Rule.objects.get_or_create(**attributes)
        return Response(serializers.RuleSerializer(rule).data, status=HTTPStatus.CREATED)


class NotifierMixin:
    @extend_schema(
        summary="Register Notifier",
        description="Register a new notifier for the specified object.",
        request=serializers.RegisterNotifierSerializer,
        responses={201: serializers.NotifierSerializer},
    )
    @action(detail=True, methods=["post"], url_path="notifiers")
    def register_notifier(self, request, id):
        object = self.get_object()
        serializer = serializers.RegisterNotifierSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        attributes = {
            "content_type_id": ContentType.objects.get_for_model(object).id,
            "object_id": object.id,
            "owner_id": request.user.id,
        }

        for field in serializer.fields:
            value = serializer.validated_data.get(field)
            if value is not None and field != "filters":
                attributes[field] = value

        notifier, created = models.Sender.objects.get_or_create(**attributes)
        for filter_data in serializer.validated_data.get("filters", []):
            models.Filter.objects.get_or_create(sender=notifier, **filter_data)
        return Response(
            serializers.NotifierSerializer(notifier).data,
            status=HTTPStatus.CREATED,
        )


class PermissionManagementMixin:
    @extend_schema(
        summary="List Users",
        description="Retrieve list of users which are members of the specified object.",
        responses=serializers.UserWithPermRetrieveSerializer(many=True),
    )
    @action(
        detail=True,
        methods=["get"],
        url_path="users",
        pagination_class=None,
        filterset_class=None,
    )
    def users(self, request, id):
        object = self.get_object()
        users_with_perm = promgen_templatetags.get_users_roles(object)
        payload = [
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": perm[0].upper(),
            }
            for user, perm in users_with_perm
        ]

        return Response(serializers.UserWithPermRetrieveSerializer(payload, many=True).data)

    @extend_schema(
        summary="Assign User",
        description="Assign permission for a user to the specified object.",
        request=serializers.PermissionAssignSerializer,
        responses=serializers.UserObjectPermissionSerializer,
    )
    @users.mapping.post
    def assign_user(self, request, id):
        object = self.get_object()
        serializer = serializers.PermissionAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = User.objects.get(id=serializer.validated_data["id"])
        if not user.is_active:
            raise ValidationError({"detail": "Cannot assign permissions to an inactive user."})
        content_type = ContentType.objects.get_for_model(object)
        permission = content_type.model + "_" + serializer.validated_data["role"].lower()
        user_object_perm = assign_perm(permission, user, object)
        return Response(
            serializers.UserObjectPermissionSerializer(user_object_perm).data,
            status=HTTPStatus.CREATED,
        )

    @extend_schema(
        summary="List Groups",
        description="Retrieve list of groups which are members of the specified object.",
        responses=serializers.GroupWithPermRetrieveSerializer(many=True),
    )
    @action(
        detail=True, methods=["get"], url_path="groups", pagination_class=None, filterset_class=None
    )
    def groups(self, request, id):
        object = self.get_object()
        groups_with_perm = promgen_templatetags.get_groups_roles(object)
        payload = [
            {
                "id": group.id,
                "name": group.name,
                "role": perm[0].upper(),
            }
            for group, perm in groups_with_perm
        ]

        return Response(serializers.GroupWithPermRetrieveSerializer(payload, many=True).data)

    @extend_schema(
        summary="Assign Group",
        description="Assign permission for a group to the specified object.",
        request=serializers.PermissionAssignSerializer,
        responses=serializers.GroupObjectPermissionSerializer,
    )
    @groups.mapping.post
    def assign_group(self, request, id):
        object = self.get_object()
        serializer = serializers.PermissionAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        group = models.Group.objects.get(id=serializer.validated_data["id"])
        content_type = ContentType.objects.get_for_model(object)
        permission = content_type.model + "_" + serializer.validated_data["role"].lower()
        group_object_perm = assign_perm(permission, group, object)
        return Response(
            serializers.GroupObjectPermissionSerializer(group_object_perm).data,
            status=HTTPStatus.CREATED,
        )

    def remove_perm(self, user_or_group, remove_sub_permissions):
        obj = self.get_object()
        permissions = get_perms(user_or_group, obj)
        for perm in permissions:
            remove_perm(perm, user_or_group, obj)

        if isinstance(obj, models.Service) and remove_sub_permissions:
            # Remove all permissions on the Service's projects
            for project in obj.project_set.all():
                permissions = get_perms(user_or_group, project)
                for perm in permissions:
                    remove_perm(perm, user_or_group, project)

                # If the removed user is the owner of the Project, we need to transfer the ownership
                # to the Service's owner and assign admin permission for them.
                if isinstance(user_or_group, User) and user_or_group == project.owner:
                    assign_perm("project_admin", obj.owner, project)
                    project.owner = obj.owner
                    project.save()

    @extend_schema(
        summary="Remove User",
        description="Remove a user from the specified object.",
        parameters=[
            OpenApiParameter(
                name="remove_sub_permissions",
                required=False,
                type=bool,
                description="Also remove permissions from sub-projects. Defaults to True.",
            )
        ],
    )
    @action(
        detail=True,
        methods=["delete"],
        url_path=r"users/(?P<user_id>\d+)",
        pagination_class=None,
        filterset_class=None,
    )
    def remove_user(self, request, id, user_id):
        remove_sub_permissions = (
            request.query_params.get("remove_sub_permissions", "true").lower() == "true"
        )
        user = User.objects.get(id=user_id)
        self.remove_perm(user, remove_sub_permissions)
        return Response(status=HTTPStatus.NO_CONTENT)

    @extend_schema(
        summary="Remove Group",
        description="Remove a group from the specified object.",
        parameters=[
            OpenApiParameter(
                name="remove_sub_permissions",
                required=False,
                type=bool,
                description="(Only use for Service) Also remove permissions from sub-projects. "
                "Defaults to True.",
            )
        ],
    )
    @action(
        detail=True,
        methods=["delete"],
        url_path=r"groups/(?P<group_id>\d+)",
        pagination_class=None,
        filterset_class=None,
    )
    def remove_group(self, request, id, group_id):
        remove_sub_permissions = (
            request.query_params.get("remove_sub_permissions", "true").lower() == "true"
        )
        group = models.Group.objects.get(id=group_id)
        self.remove_perm(group, remove_sub_permissions)
        return Response(status=HTTPStatus.NO_CONTENT)


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

    def get_serializer_class(self):
        if self.action in ["update", "partial_update"]:
            return serializers.ExporterUpdateSerializer
        return serializers.ExporterRetrieveSerializer


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

    def get_serializer_class(self):
        if self.action == "retrieve":
            return serializers.GroupRetrieveDetailSerializer
        return serializers.GroupRetrieveSerializer

    @extend_schema(
        summary="Add Members",
        description="Add list of members to the group.",
        request=serializers.AddMemberGroupSerializer,
        responses=serializers.GroupRetrieveDetailSerializer,
    )
    @action(detail=True, methods=["post"], url_path="members")
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

        return Response(serializers.GroupRetrieveDetailSerializer(group).data)

    @extend_schema(
        summary="Update Member",
        description="Change role of a member in the group.",
        request=serializers.UpdateMemberGroupSerializer,
        responses=serializers.GroupRetrieveDetailSerializer,
    )
    @action(
        detail=True,
        methods=["put"],
        url_path=r"members/(?P<user_id>\d+)",
        pagination_class=None,
        filterset_class=None,
    )
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

        return Response(serializers.GroupRetrieveDetailSerializer(group).data)

    @extend_schema(
        summary="Remove Member",
        description="Remove a member from the group.",
        responses={
            "204": serializers.GroupRetrieveDetailSerializer,
        },
    )
    @update_member.mapping.delete
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

        return Response(serializers.GroupRetrieveDetailSerializer(group).data)


@extend_schema_view(
    list=extend_schema(summary="List Projects", description="Retrieve a list of all projects."),
    retrieve=extend_schema(
        summary="Retrieve Project",
        description="Retrieve detailed information about a specific project.",
        parameters=[
            OpenApiParameter(
                name="extra_fields",
                required=False,
                type=str,
                description=(
                    "Optional comma-separated extra fields to include in response. "
                    "Supported values: farm, notifiers, rules, urls. "
                    "Example: extra_fields=rules,urls"
                ),
            )
        ],
    ),
    update=extend_schema(summary="Update Project", description="Update an existing project."),
    partial_update=extend_schema(
        summary="Partially Update Project", description="Partially update an existing project."
    ),
    destroy=extend_schema(summary="Delete Project", description="Delete an existing project."),
)
@extend_schema(tags=["Project"])
class ProjectViewSet(
    NotifierMixin,
    RuleMixin,
    PermissionManagementMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = models.Project.objects.all()
    filterset_class = filters.ProjectFilterV2
    lookup_value_regex = "[^/]+"
    lookup_field = "id"
    pagination_class = PromgenPagination
    permission_classes = [permissions.PromgenGuardianRestPermission]

    def get_queryset(self):
        if self.request.user.is_superuser or self.action != "list":
            return self.queryset
        return permissions.get_accessible_projects_for_user(self.request.user)

    def get_serializer_class(self):
        if self.action in ["list", "update", "partial_update"]:
            return serializers.ProjectRetrieveSimpleSerializer
        if self.action == "retrieve":
            return serializers.ProjectRetrieveDetailSerializer
        return serializers.ProjectRetrieveDetailSerializer

    def perform_update(self, serializer):
        project = self.get_object()
        original_owner_id = project.owner_id
        new_owner = serializer.validated_data.get("owner")
        owner_changed = new_owner is not None and new_owner.id != original_owner_id

        if owner_changed and not (
            self.request.user.is_superuser or self.request.user.id == original_owner_id
        ):
            raise ValidationError({"owner": "You do not have permission to change the owner."})

        super().perform_update(serializer)

        if owner_changed:
            assign_perm("project_admin", new_owner, project)

    def destroy(self, request, *args, **kwargs):
        project = self.get_object()
        if (
            not request.user.is_superuser
            and project.owner != request.user
            and project.service.owner != request.user
        ):
            raise PermissionDenied("Only the project or the service owner can delete the project.")
        return super().destroy(request, *args, **kwargs)

    @extend_schema(
        summary="Register Farm",
        description="Register a new farm for the specified project.",
        request=serializers.RegisterURLProjectSerializer,
        responses={201: serializers.FarmRetrieveSerializer},
    )
    @action(detail=True, methods=["post"], url_path="farms")
    def register_farm(self, request, id):
        project = self.get_object()
        serializer = serializers.FarmRetrieveSerializer
        serializer.is_valid(raise_exception=True)

        farm = models.Farm.objects.get_or_create(
            project=project,
        )
        return Response(serializers.FarmRetrieveSerializer(farm).data, status=HTTPStatus.CREATED)

    @extend_schema(
        summary="Link Farm",
        description="Link a farm to the specified project.",
        request=serializers.LinkFarmSerializer,
        responses=serializers.FarmRetrieveSerializer,
    )
    @action(detail=True, methods=["post"], url_path="farms/link")
    def link_farm(self, request, id):
        project = self.get_object()
        serializer = serializers.LinkFarmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        driver = None
        for driver_name, farm_driver in models.Farm.driver_set():
            if driver_name == serializer.validated_data["source"]:
                driver = farm_driver
                break

        if driver is None:
            raise ValidationError({"source": "Unknown farm source."})
        if not driver.remote:
            raise ValidationError({"source": "Only remote farm sources are supported."})

        if serializer.validated_data["farm"] not in set(
            models.Farm.fetch(serializer.validated_data["source"])
        ):
            raise ValidationError({"farm": "Unknown farm."})

        farm, created = models.Farm.objects.get_or_create(
            name=serializer.validated_data["farm"],
            source=serializer.validated_data["source"],
            project=project,
        )
        if created:
            farm.refresh()
        project.farm = farm
        project.save()
        return Response(serializers.FarmRetrieveSerializer(project.farm).data)

    @extend_schema(
        summary="Unlink Farm",
        description="Unlink the farm from the specified project.",
        responses=serializers.ProjectRetrieveDetailSerializer,
    )
    @action(detail=True, methods=["post"], url_path="farms/unlink")
    def unlink_farm(self, request, id):
        project = self.get_object()
        if project.farm is None:
            return Response(
                serializers.ProjectRetrieveDetailSerializer(
                    project, context=self.get_serializer_context()
                ).data
            )

        oldfarm, project.farm = project.farm, None
        project.save()
        signals.trigger_write_config.send(request)

        oldfarm.delete()
        return Response(
            serializers.ProjectRetrieveDetailSerializer(
                project, context=self.get_serializer_context()
            ).data
        )

    @extend_schema(
        summary="Register URL",
        description="Register a new URL for the specified project.",
        request=serializers.RegisterURLProjectSerializer,
        responses={201: serializers.URLSerializer},
    )
    @action(detail=True, methods=["post"], url_path="urls")
    def register_url(self, request, id):
        project = self.get_object()
        serializer = serializers.RegisterURLProjectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        url, created = models.URL.objects.get_or_create(
            project=project,
            url=serializer.validated_data["url"],
            probe=serializer.validated_data["probe"],
        )
        return Response(serializers.URLSerializer(url).data, status=HTTPStatus.CREATED)

    @extend_schema(
        summary="Register Exporter",
        description="Register a new exporter for the specified project.",
        request=serializers.RegisterExporterProjectSerializer,
        responses={201: serializers.ExporterRetrieveSerializer},
    )
    @action(detail=True, methods=["post"], url_path="exporters")
    def register_exporter(self, request, id):
        project = self.get_object()
        serializer = serializers.RegisterExporterProjectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        attributes = {
            "project_id": project.id,
        }

        for field in serializer.fields:
            value = serializer.validated_data.get(field)
            if value is not None:
                attributes[field] = value

        exporter, created = models.Exporter.objects.get_or_create(**attributes)
        return Response(
            serializers.ExporterRetrieveSerializer(exporter).data,
            status=HTTPStatus.CREATED,
        )


@extend_schema_view(
    list=extend_schema(
        summary="List Services",
        description="Retrieve a list of all services.",
    ),
    retrieve=extend_schema(
        summary="Retrieve Service",
        description="Retrieve detailed information about a specific service.",
        parameters=[
            OpenApiParameter(
                name="extra_fields",
                required=False,
                type=str,
                description=(
                    "Optional comma-separated extra fields to include in response. "
                    "Supported values: notifiers, projects, rules. "
                    "Example: extra_fields=projects,notifiers"
                ),
            )
        ],
    ),
    create=extend_schema(summary="Create Service", description="Create a new service."),
    update=extend_schema(summary="Update Service", description="Update an existing service."),
    partial_update=extend_schema(
        summary="Partially Update Service", description="Partially update an existing service."
    ),
    destroy=extend_schema(summary="Delete Service", description="Delete an existing service."),
)
@extend_schema(tags=["Service"])
class ServiceViewSet(NotifierMixin, RuleMixin, PermissionManagementMixin, viewsets.ModelViewSet):
    queryset = models.Service.objects.all()
    filterset_class = filters.ServiceFilterV2
    serializer_class = serializers.ServiceSerializer
    lookup_value_regex = "[^/]+"
    lookup_field = "id"
    pagination_class = PromgenPagination
    permission_classes = [permissions.PromgenGuardianRestPermission]

    def get_queryset(self):
        if self.request.user.is_superuser or self.action != "list":
            return self.queryset
        return permissions.get_accessible_services_for_user(self.request.user)

    def get_serializer_class(self):
        if self.action == "create":
            return serializers.ServiceRegisterSerializer
        if self.action == "retrieve":
            return serializers.ServiceRetrieveDetailSerializer
        return serializers.ServiceRetrieveSimpleSerializer

    def perform_update(self, serializer):
        service = self.get_object()
        original_owner_id = service.owner_id
        new_owner = serializer.validated_data.get("owner")
        owner_changed = new_owner is not None and new_owner.id != original_owner_id

        if owner_changed and not (
            self.request.user.is_superuser or self.request.user.id == original_owner_id
        ):
            raise ValidationError({"owner": "You do not have permission to change the owner."})

        super().perform_update(serializer)

        if owner_changed:
            assign_perm("service_admin", new_owner, service)

    def destroy(self, request, *args, **kwargs):
        service = self.get_object()
        if not request.user.is_superuser and service.owner != request.user:
            raise PermissionDenied("Only the service owner can delete the service.")
        return super().destroy(request, *args, **kwargs)

    @extend_schema(
        summary="Register Project",
        description="Register a new project for the specified service.",
        request=serializers.RegisterProjectServiceSerializer,
        responses={201: serializers.ProjectRetrieveSimpleSerializer},
    )
    @action(detail=True, methods=["post"], url_path="projects")
    def register_project(self, request, id):
        service = self.get_object()
        serializer = serializers.RegisterProjectServiceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        attributes = {"service": service, "owner_id": request.user.id}

        for field in serializer.fields:
            value = serializer.validated_data.get(field)
            if value is not None:
                attributes[field] = value

        project, _ = models.Project.objects.get_or_create(**attributes)
        return Response(
            serializers.ProjectRetrieveSimpleSerializer(project).data, status=HTTPStatus.CREATED
        )


@extend_schema_view(
    list=extend_schema(summary="List Shards", description="Retrieve a list of all shards."),
)
@extend_schema(tags=["Shard"])
class ShardViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = models.Shard.objects.all()
    filterset_class = filters.ShardFilter
    serializer_class = serializers.ShardRetrieveSerializer
    lookup_field = "id"
    pagination_class = PromgenPagination


@extend_schema_view(
    list=extend_schema(summary="List Users", description="Retrieve a list of all users."),
)
@extend_schema(tags=["User"])
class UserViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = (
        User.objects.filter(is_active=True)
        .exclude(username=ANONYMOUS_USER_NAME)
        .order_by("username")
    )
    filterset_class = filters.UserFilter
    serializer_class = serializers.UserRetrieveSimpleSerializer
    lookup_value_regex = "[^/]+"
    pagination_class = PromgenPagination
    permission_classes = [permissions.PromgenGuardianRestPermission]

    @extend_schema(
        summary="Get Current User",
        description="Retrieve the current authenticated user's information.",
        responses=serializers.UserRetrieveDetailSerializer,
    )
    @action(detail=False, methods=["get"], url_path="me")
    def get_current_user(self, request):
        return Response(serializers.UserRetrieveDetailSerializer(request.user).data)

    @extend_schema(
        summary="Register User's Notifier",
        description="Register a new notifier for the current user.",
        request=serializers.RegisterNotifierSerializer,
        responses={201: serializers.NotifierSerializer},
    )
    @action(detail=False, methods=["post"], url_path="me/notifiers")
    def register_notifier(self, request):
        user = request.user
        serializer = serializers.RegisterNotifierSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if serializer.validated_data.get("sender") == "promgen.notification.user":
            return Response(
                {"detail": "Cannot register a promgen.notification.user notifier for a user."},
                status=HTTPStatus.BAD_REQUEST,
            )

        attributes = {
            "content_type_id": ContentType.objects.get_for_model(user).id,
            "object_id": user.id,
            "owner_id": user.id,
        }

        for field in serializer.fields:
            value = serializer.validated_data.get(field)
            if value is not None and field != "filters":
                attributes[field] = value

        notifier, created = models.Sender.objects.get_or_create(**attributes)
        for filter_data in serializer.validated_data.get("filters", []):
            models.Filter.objects.get_or_create(sender=notifier, **filter_data)
        return Response(
            serializers.NotifierSerializer(notifier).data,
            status=HTTPStatus.CREATED,
        )
