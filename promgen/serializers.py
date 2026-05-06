import collections

from dateutil import parser
from django.contrib.auth.models import User
from django.db.models import prefetch_related_objects
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from guardian.models import GroupObjectPermission, UserObjectPermission
from rest_framework import serializers

import promgen.templatetags.promgen as macro
from promgen import errors, models, shortcuts
from promgen.shortcuts import resolve_domain


class WebLinkField(serializers.Field):
    def get_attribute(self, instance):
        return instance

    def to_representation(self, obj):
        return shortcuts.resolve_domain(obj.get_absolute_url())


class ShardSerializer(serializers.ModelSerializer):
    html = WebLinkField()

    class Meta:
        model = models.Shard
        exclude = ("id", "authorization")
        lookup_field = "name"


class ServiceSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source="owner.username")
    shard = serializers.ReadOnlyField(source="shard.name")
    html = WebLinkField()

    class Meta:
        model = models.Service
        exclude = ("id",)
        lookup_field = "name"


class ProjectSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source="owner.username")
    service = serializers.ReadOnlyField(source="service.name")
    shard = serializers.ReadOnlyField(source="service.shard.name")
    html = WebLinkField()

    class Meta:
        model = models.Project
        lookup_field = "name"
        exclude = ("id",)


class SenderSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source="owner.username")
    label = serializers.ReadOnlyField(source="show_value")

    class Meta:
        model = models.Sender
        fields = "__all__"


class AlertRuleList(serializers.ListSerializer):
    def to_representation(self, data):
        grouped_list = collections.defaultdict(list)
        for item in data:
            data = self.child.to_representation(item)
            grouped_list[str(item.content_object)].append(data)
        return grouped_list

    @property
    def data(self):
        if not hasattr(self, "_data"):
            self._data = self.to_representation(self.instance)
        return serializers.ReturnDict(self._data, serializer=self)


class AlertRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Rule
        fields = ("alert", "expr", "for", "labels", "annotations")

    @classmethod
    def many_init(cls, queryset, *args, **kwargs):
        # when rendering many items at once, we want to make sure we
        # do our prefetch operations in one go, before passing it off
        # to our custom list renderer to group things in a dictionary
        kwargs["child"] = cls()
        prefetch_related_objects(
            queryset,
            "content_object",
            "content_type",
            "overrides__content_object",
            "overrides__content_type",
        )
        return AlertRuleList(queryset, *args, **kwargs)

    def to_representation(self, obj):
        annotations = obj.annotations
        annotations["rule"] = resolve_domain("rule-detail", pk=obj.pk if obj.pk else 0)

        return {
            "alert": obj.name,
            "expr": macro.rulemacro(obj),
            "for": obj.duration,
            "labels": obj.labels,
            "annotations": annotations,
        }


class FarmSerializer(serializers.ModelSerializer):
    url = WebLinkField()

    class Meta:
        model = models.Farm
        fields = "__all__"


class HostSerializer(serializers.ModelSerializer):
    url = WebLinkField()

    class Meta:
        model = models.Host
        exclude = ("id", "farm")


class MatcherSerializer(serializers.Serializer):
    name = serializers.CharField()
    value = serializers.CharField()
    isRegex = serializers.BooleanField()
    isEqual = serializers.BooleanField(default=True)


class SilenceSerializer(serializers.Serializer):
    id = serializers.CharField(required=False)
    matchers = MatcherSerializer(many=True)
    startsAt = serializers.CharField(required=False)
    endsAt = serializers.CharField(required=False)
    createdBy = serializers.CharField()
    comment = serializers.CharField(default="Silenced from Promgen")
    duration = serializers.CharField(required=False)

    def validate(self, data):
        # Validation for matchers
        if "matchers" not in data or not data["matchers"]:
            raise errors.SilenceError.NOMATCHER.error()

        # Every silence should include either a service or project matcher
        if not any(matcher["name"] in ["service", "project"] for matcher in data["matchers"]):
            raise errors.SilenceError.NOSERVICEORPROJECTMATCHER.error()

        if data.get("duration"):
            # No further validation is required if only duration is set
            return data

        # Validate our start/end times
        start = data.get("startsAt")
        stop = data.get("endsAt")

        if not all([start, stop]):
            raise errors.SilenceError.STARTENDTIME.error()

        elif parser.parse(start) > parser.parse(stop):
            raise errors.SilenceError.STARTENDMISMATCH.error()

        return data


class AuditSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source="user.username")
    log = serializers.ReadOnlyField(source="body")
    content_type = serializers.ReadOnlyField(source="content_type.model")
    new = serializers.ReadOnlyField(source="data")

    class Meta:
        model = models.Audit
        fields = ("user", "content_type", "object_id", "log", "created", "new", "old")


class FilterSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Filter
        fields = ["id", "name", "value"]


class NotifierSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source="owner.username")
    content_name = serializers.SerializerMethodField()
    content_type = serializers.ReadOnlyField(source="content_type.model")
    filters = FilterSerializer(many=True, read_only=True, source="filter_set")

    class Meta:
        model = models.Sender
        exclude = ("object_id",)

    def get_content_name(self, obj) -> str:
        if hasattr(obj, "content_object"):
            if hasattr(obj.content_object, "name"):
                return obj.content_object.name
            if hasattr(obj.content_object, "username"):
                return obj.content_object.username
        return None


class UpdateNotifierSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Sender
        fields = ["enabled"]


@extend_schema_field(OpenApiTypes.STR)
class RuleField(serializers.Field):
    def to_internal_value(self, data):
        try:
            rule = models.Rule.objects.get(pk=data)
        except models.Rule.DoesNotExist:
            raise serializers.ValidationError("Owner does not exist.")
        return rule

    def to_representation(self, value):
        return value.name


class RuleSerializer(serializers.ModelSerializer):
    content_name = serializers.SerializerMethodField()
    content_type = serializers.ReadOnlyField(source="content_type.model")
    labels = serializers.JSONField(required=False)
    annotations = serializers.JSONField(required=False)
    parent = RuleField(required=False)

    class Meta:
        model = models.Rule
        exclude = ("object_id",)

    def get_content_name(self, obj) -> str:
        if hasattr(obj, "content_object"):
            return obj.content_object.name
        return None


class HostRetrieveSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Host
        fields = "__all__"


class FarmRetrieveSerializer(serializers.ModelSerializer):
    project = serializers.ReadOnlyField(source="project.name")

    class Meta:
        model = models.Farm
        fields = "__all__"


class FarmUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Farm
        exclude = ("id", "project", "source")


class HostListSerializer(serializers.Serializer):
    hosts = serializers.ListField(
        child=serializers.CharField(), help_text="List of hostnames to add."
    )


class FarmSourceSerializer(serializers.Serializer):
    name = serializers.CharField()
    remote = serializers.BooleanField()


class RemoteFarmSerializer(serializers.Serializer):
    name = serializers.CharField()


class ExporterRetrieveSerializer(serializers.ModelSerializer):
    project = serializers.ReadOnlyField(source="project.name")

    class Meta:
        model = models.Exporter
        fields = "__all__"


class ExporterUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Exporter
        fields = "__all__"
        read_only_fields = (
            "job",
            "port",
            "path",
            "scheme",
            "project",
        )


class URLSerializer(serializers.ModelSerializer):
    project = serializers.ReadOnlyField(source="project.name")
    probe = serializers.ReadOnlyField(source="probe.module")

    class Meta:
        model = models.URL
        fields = "__all__"


class GroupRetrieveSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Group
        fields = (
            "id",
            "name",
        )


class UserWithPermRetrieveSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    email = serializers.EmailField()
    role = serializers.CharField()


class GroupAssignedResourceSerializer(serializers.Serializer):
    content_type = serializers.CharField()
    name = serializers.CharField()
    role = serializers.CharField()


class GroupRetrieveDetailSerializer(serializers.ModelSerializer):
    members = UserWithPermRetrieveSerializer(many=True, required=False, read_only=True)
    assigned_resources = GroupAssignedResourceSerializer(many=True, required=False, read_only=True)

    class Meta:
        model = models.Group
        fields = (
            "id",
            "name",
            "members",
            "assigned_resources",
        )

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        users_with_perm = macro.get_users_roles(instance)
        representation["members"] = []
        for user, perm in users_with_perm:
            representation["members"].append(
                {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": perm[0].upper(),
                }
            )

        assigned_resources = GroupObjectPermission.objects.filter(group=instance)
        representation["assigned_resources"] = []
        for assigned_resource in assigned_resources:
            representation["assigned_resources"].append(
                {
                    "content_type": assigned_resource.content_type.model,
                    "name": assigned_resource.content_object.name,
                    "role": assigned_resource.permission.codename.split("_")[1].upper(),
                }
            )

        return representation


class AddMemberGroupSerializer(serializers.Serializer):
    user_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
    )
    group_role = serializers.ChoiceField(choices=["ADMIN", "MEMBER"])


class UpdateMemberGroupSerializer(serializers.Serializer):
    group_role = serializers.ChoiceField(choices=["ADMIN", "MEMBER"])


@extend_schema_field(OpenApiTypes.STR)
class ServiceField(serializers.Field):
    def to_internal_value(self, data):
        try:
            service = models.Service.objects.get(name=data)
        except models.Service.DoesNotExist:
            raise serializers.ValidationError("Service does not exist.")
        return service

    def to_representation(self, value):
        return value.name


@extend_schema_field(OpenApiTypes.STR)
class ShardField(serializers.Field):
    def to_internal_value(self, data):
        try:
            shard = models.Shard.objects.get(name=data)
        except models.Shard.DoesNotExist:
            raise serializers.ValidationError("Shard does not exist.")
        return shard

    def to_representation(self, value):
        return value.name


@extend_schema_field(OpenApiTypes.STR)
class OwnerField(serializers.Field):
    def to_internal_value(self, data):
        if not data:
            return serializers.CurrentUserDefault()
        try:
            owner = User.objects.get(username=data)
            if not owner.is_active:
                raise serializers.ValidationError("owner is not active.")
        except User.DoesNotExist:
            raise serializers.ValidationError("Owner does not exist.")
        return owner

    def to_representation(self, value):
        return value.username


class GroupWithPermRetrieveSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    role = serializers.CharField()


class PermissionAssignSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    role = serializers.ChoiceField(choices=["ADMIN", "EDITOR", "VIEWER"])


class ProjectRetrieveSimpleSerializer(serializers.ModelSerializer):
    owner = OwnerField()
    service = ServiceField()
    shard = ShardField()

    class Meta:
        model = models.Project
        fields = "__all__"


class ProjectRetrieveDetailSerializer(serializers.ModelSerializer):
    EXTRA_FIELDS = {"farm", "notifiers", "rules", "urls"}

    owner = OwnerField()
    service = ServiceField()
    shard = ShardField()
    farm = FarmRetrieveSerializer()
    rules = RuleSerializer(many=True, read_only=True, source="rule_set")
    notifiers = NotifierSerializer(many=True, read_only=True)
    urls = URLSerializer(many=True, read_only=True, source="url_set")

    class Meta:
        model = models.Project
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        requested_extra_fields = self._get_requested_extra_fields()
        if requested_extra_fields is None:
            for field in self.EXTRA_FIELDS:
                self.fields.pop(field, None)
            return

        for field in self.EXTRA_FIELDS - requested_extra_fields:
            self.fields.pop(field, None)

    def _get_requested_extra_fields(self):
        request = self.context.get("request")
        if request is None:
            return None

        if "extra_fields" not in request.query_params:
            return None

        requested_fields = set()
        for raw_value in request.query_params.getlist("extra_fields"):
            for value in raw_value.split(","):
                value = value.strip()
                if value:
                    requested_fields.add(value)

        return requested_fields & self.EXTRA_FIELDS


class ProjectUpdateSerializer(serializers.ModelSerializer):
    owner = OwnerField(required=False)
    service = ServiceField(required=False, read_only=True)
    shard = ShardField(required=False)
    farm = serializers.ReadOnlyField(source="farm.name")
    name = serializers.CharField(required=False)

    class Meta:
        model = models.Project
        fields = "__all__"


class LinkFarmSerializer(serializers.Serializer):
    farm = serializers.CharField()
    source = serializers.CharField()


@extend_schema_field(OpenApiTypes.STR)
class ProbeField(serializers.Field):
    def to_internal_value(self, data):
        try:
            probe = models.Probe.objects.get(module=data)
        except models.Probe.DoesNotExist:
            raise serializers.ValidationError("Probe does not exist.")
        return probe

    def to_representation(self, value):
        return value.module


class RegisterURLProjectSerializer(serializers.ModelSerializer):
    probe = ProbeField()

    class Meta:
        model = models.URL
        fields = ("url", "probe")


class RegisterExporterProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Exporter
        fields = ("job", "port", "path", "scheme", "enabled")


class RegisterNotifierSerializer(serializers.Serializer):
    sender = serializers.ChoiceField(choices=[name for name, _ in models.Sender.driver_set()])
    value = serializers.CharField()
    alias = serializers.CharField(required=False)
    enabled = serializers.BooleanField(required=False, default=True)
    filters = FilterSerializer(many=True, required=False)


class UserObjectPermissionSerializer(serializers.ModelSerializer):
    object = serializers.CharField(source="content_object.name", required=True)
    permission = serializers.CharField(source="permission.codename", required=True)
    user = serializers.CharField(source="user.username", required=True)

    class Meta:
        model = UserObjectPermission
        fields = (
            "id",
            "object",
            "permission",
            "user",
        )


class GroupObjectPermissionSerializer(serializers.ModelSerializer):
    object = serializers.CharField(source="content_object.name", required=True)
    permission = serializers.CharField(source="permission.codename", required=True)
    group = serializers.CharField(source="group.name", required=True)

    class Meta:
        model = UserObjectPermission
        fields = (
            "id",
            "group",
            "object",
            "permission",
        )


class ServiceRegisterSerializer(serializers.ModelSerializer):
    owner = OwnerField(read_only=True)

    class Meta:
        model = models.Service
        fields = "__all__"

    def create(self, validated_data):
        validated_data["owner"] = self.context["request"].user
        return super().create(validated_data)


class ServiceRetrieveSimpleSerializer(serializers.ModelSerializer):
    owner = OwnerField()

    class Meta:
        model = models.Service
        fields = "__all__"


class ServiceRetrieveDetailSerializer(serializers.ModelSerializer):
    EXTRA_FIELDS = {"notifiers", "projects", "rules"}

    owner = OwnerField()
    projects = ProjectRetrieveSimpleSerializer(many=True, read_only=True, source="project_set")
    rules = RuleSerializer(many=True, read_only=True, source="rule_set")
    notifiers = NotifierSerializer(many=True, read_only=True)

    class Meta:
        model = models.Service
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        requested_extra_fields = self._get_requested_extra_fields()
        if requested_extra_fields is None:
            for field in self.EXTRA_FIELDS:
                self.fields.pop(field, None)
            return

        for field in self.EXTRA_FIELDS - requested_extra_fields:
            self.fields.pop(field, None)

    def _get_requested_extra_fields(self):
        request = self.context.get("request")
        if request is None:
            return None

        if "extra_fields" not in request.query_params:
            return None

        requested_fields = set()
        for raw_value in request.query_params.getlist("extra_fields"):
            for value in raw_value.split(","):
                value = value.strip()
                if value:
                    requested_fields.add(value)

        return requested_fields & self.EXTRA_FIELDS


class RegisterProjectServiceSerializer(serializers.ModelSerializer):
    shard = ShardField()
    owner = OwnerField(read_only=True)

    class Meta:
        model = models.Project
        fields = "__all__"
        read_only_fields = ("service",)


class ShardRetrieveSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Shard
        exclude = ("authorization",)


class UserRetrieveSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name")


class UserSubscriptionSerializer(serializers.Serializer):
    services = ServiceRetrieveSimpleSerializer(many=True)
    projects = ProjectRetrieveSimpleSerializer(many=True)


class UserRetrieveDetailSerializer(serializers.ModelSerializer):
    notifiers = NotifierSerializer(many=True, required=False, read_only=True)
    subscriptions = UserSubscriptionSerializer(required=False, read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_staff",
            "is_superuser",
            "notifiers",
            "subscriptions",
        )

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        representation["notifiers"] = NotifierSerializer(
            models.Sender.objects.filter(obj=instance), many=True
        ).data
        subscriptions = models.Sender.objects.filter(
            sender="promgen.notification.user", value=str(instance.pk)
        )

        subscribed_services = []
        subscribed_projects = []
        for notifier in subscriptions:
            if notifier.content_type.model == "service":
                subscribed_services.append(notifier.content_object)
            elif notifier.content_type.model == "project":
                subscribed_projects.append(notifier.content_object)

        representation["subscriptions"] = {
            "services": ServiceRetrieveSimpleSerializer(subscribed_services, many=True).data,
            "projects": ProjectRetrieveSimpleSerializer(subscribed_projects, many=True).data,
        }

        return representation


class RuleTestResultSerializer(serializers.Serializer):
    duration = serializers.DurationField(read_only=True)
    firing = serializers.BooleanField(read_only=True)
    errors = serializers.DictField(child=serializers.CharField(), read_only=True)
