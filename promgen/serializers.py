import collections

from dateutil import parser
from django.db.models import prefetch_related_objects
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from guardian.models import UserObjectPermission
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
    parent_content_type = serializers.ReadOnlyField(source="parent_content_type.model")

    class Meta:
        model = models.Audit
        fields = (
            "id",
            "user",
            "content_type",
            "object_id",
            "log",
            "created",
            "new",
            "old",
            "parent_content_type",
            "parent_object_id",
        )


class FilterSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Filter
        fields = ["id", "name", "value"]


class NotifierSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source="owner.username")
    content_name = serializers.SerializerMethodField()
    content_type = serializers.ReadOnlyField(source="content_type.model")
    filters = FilterSerializer(many=True, read_only=True, source="filter_set")
    value = serializers.SerializerMethodField(
        method_name="get_notifier_value",
        help_text="If an alias is set, the value will be hidden as null.",
    )
    alias = serializers.CharField(
        help_text="Use to hide the notifier's value from being displayed."
    )

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

    def get_notifier_value(self, obj) -> str:
        if obj.alias:
            return None
        return obj.value


class UpdateNotifierSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Sender
        fields = ["enabled"]


class RuleRetrieveSimpleSerializer(serializers.ModelSerializer):
    content_name = serializers.CharField(read_only=True, source="content_object.name")
    content_type = serializers.CharField(read_only=True, source="content_type.model")

    class Meta:
        model = models.Rule
        exclude = (
            "description",
            "annotations",
            "labels",
            "object_id",
        )


class RuleRetrieveDetailSerializer(serializers.ModelSerializer):
    content_name = serializers.CharField(read_only=True, source="content_object.name")
    content_type = serializers.CharField(read_only=True, source="content_type.model")

    class Meta:
        model = models.Rule
        fields = "__all__"
        read_only_fields = (
            "parent",
            "object_id",
        )


class HostRetrieveSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Host
        fields = "__all__"


class FarmRetrieveSerializer(serializers.ModelSerializer):
    project = serializers.ReadOnlyField(source="project.name")
    project_id = serializers.ReadOnlyField(source="project.id")
    remote = serializers.SerializerMethodField()

    class Meta:
        model = models.Farm
        fields = "__all__"
        read_only_fields = ("id", "project", "source")

    def get_remote(self, obj) -> bool:
        return obj.driver.remote


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
    project_id = serializers.ReadOnlyField(source="project.id")

    class Meta:
        model = models.Exporter
        fields = "__all__"
        read_only_fields = ("job", "port", "path", "scheme", "project")


class URLSerializer(serializers.ModelSerializer):
    project = serializers.ReadOnlyField(source="project.name")
    probe = serializers.ReadOnlyField(source="probe.module")

    class Meta:
        model = models.URL
        fields = "__all__"


class ProbeSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Probe
        fields = "__all__"


class GroupRetrieveSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Group
        fields = ("id", "name")


class UserWithPermRetrieveSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    email = serializers.EmailField()
    role = serializers.CharField()


class GroupAssignedResourceSerializer(serializers.Serializer):
    content_type = serializers.CharField()
    object_id = serializers.IntegerField()
    name = serializers.CharField()
    role = serializers.CharField()


class AddMemberGroupSerializer(serializers.Serializer):
    user_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
    )
    group_role = serializers.ChoiceField(choices=["ADMIN", "MEMBER"])


class UpdateMemberGroupSerializer(serializers.Serializer):
    group_role = serializers.ChoiceField(choices=["ADMIN", "MEMBER"])


class ShardRetrieveSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Shard
        exclude = ("authorization",)


class ServiceRetrieveSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Service
        fields = "__all__"


class GroupWithPermRetrieveSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    role = serializers.CharField()


class PermissionAssignSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    role = serializers.ChoiceField(choices=["ADMIN", "EDITOR", "VIEWER"])


class ProjectSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Project
        fields = "__all__"


class ProjectRetrieveDetailSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source="owner.username")
    owner_id = serializers.ReadOnlyField(source="owner.id")
    service = ServiceRetrieveSimpleSerializer()
    shard = ShardRetrieveSerializer()
    farm = FarmRetrieveSerializer()

    class Meta:
        model = models.Project
        fields = "__all__"


class RegisterFarmToProjectSerializer(serializers.ModelSerializer):
    source = serializers.CharField()
    hosts = serializers.ListField(
        required=False,
        child=serializers.CharField(),
        help_text="List of hostnames. Only used when registering a local farm.",
    )

    class Meta:
        model = models.Farm
        fields = ("name", "hosts", "source")


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


class RegisterURLToProjectSerializer(serializers.ModelSerializer):
    probe = ProbeField()

    class Meta:
        model = models.URL
        fields = ("url", "probe")


class RegisterExporterToProjectSerializer(serializers.ModelSerializer):
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
        fields = ("id", "object", "permission", "user")


class GroupObjectPermissionSerializer(serializers.ModelSerializer):
    object = serializers.CharField(source="content_object.name", required=True)
    permission = serializers.CharField(source="permission.codename", required=True)
    group = serializers.CharField(source="group.name", required=True)

    class Meta:
        model = UserObjectPermission
        fields = ("id", "group", "object", "permission")
