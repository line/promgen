import collections

from dateutil import parser
from django.db.models import prefetch_related_objects
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from guardian.models import GroupObjectPermission
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
