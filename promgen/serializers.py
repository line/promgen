import collections

from django.contrib.auth.models import User
from django.db.models import prefetch_related_objects
from rest_framework import serializers

import promgen.templatetags.promgen as macro
from promgen import models, shortcuts
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
        exclude = ("id", "farm")


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
        fields = '__all__'


class HostSerializer(serializers.ModelSerializer):
    url = WebLinkField()

    class Meta:
        model = models.Host
        exclude = ("id", "farm")


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name")


class CurrentUserSerializer(serializers.ModelSerializer):
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
            "date_joined",
            "last_login",
        )


class AuditSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source="user.username")
    log = serializers.ReadOnlyField(source="body")
    content_type = serializers.ReadOnlyField(source="content_type.model")
    new = serializers.ReadOnlyField(source="data")

    class Meta:
        model = models.Audit
        fields = ("user", "content_type", "object_id", "log", "created", "new", "old")


class OwnerField(serializers.Field):
    def to_internal_value(self, data):
        if not data:
            return serializers.CurrentUserDefault()
        try:
            owner = User.objects.get(username=data)
        except User.DoesNotExist:
            raise serializers.ValidationError("Owner does not exist.")
        return owner

    def to_representation(self, value):
        return value.username


class FilterSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Filter
        fields = ["name", "value"]


class NotifierSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source="owner.username")
    content_name = serializers.ReadOnlyField(source="content_object.name")
    content_type = serializers.ReadOnlyField(source="content_type.model")
    filters = FilterSerializer(many=True, read_only=True, source="filter_set")

    class Meta:
        model = models.Sender
        exclude = ("object_id",)


class UpdateNotifierSerializer(serializers.Serializer):
    enabled = serializers.BooleanField()


class RuleField(serializers.Field):
    def to_internal_value(self, data):
        try:
            rule = models.Rule.get(pk=data)
        except models.Rule.DoesNotExist:
            raise serializers.ValidationError("Owner does not exist.")
        return rule


class RuleSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source="owner.username")
    content_name = serializers.ReadOnlyField(source="content_object.name")
    content_type = serializers.ReadOnlyField(source="content_type.model")
    labels = serializers.JSONField(required=False)
    annotations = serializers.JSONField(required=False)
    parent = RuleField(required=False)

    class Meta:
        model = models.Rule
        exclude = ("object_id",)


class HostRetrieveSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Host
        fields = "__all__"


class FarmRetrieveSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Farm
        fields = "__all__"


class HostListSerializer(serializers.Serializer):
    hosts = serializers.ListField(
        child=serializers.CharField(), help_text="List of hostnames to add."
    )


class ExporterSerializer(serializers.ModelSerializer):
    project = serializers.ReadOnlyField(source="project.name")

    class Meta:
        model = models.Exporter
        fields = "__all__"


class URLSerializer(serializers.ModelSerializer):
    project = serializers.ReadOnlyField(source="project.name")
    probe = serializers.ReadOnlyField(source="probe.module")

    class Meta:
        model = models.URL
        fields = "__all__"


class ServiceField(serializers.Field):
    def to_internal_value(self, data):
        try:
            service = models.Service.objects.get(name=data)
        except models.Service.DoesNotExist:
            raise serializers.ValidationError("Service does not exist.")
        return service

    def to_representation(self, value):
        return value.name


class ShardField(serializers.Field):
    def to_internal_value(self, data):
        try:
            shard = models.Shard.objects.get(name=data)
        except models.Shard.DoesNotExist:
            raise serializers.ValidationError("Shard does not exist.")
        return shard

    def to_representation(self, value):
        return value.name


class FarmField(serializers.Field):
    def to_internal_value(self, data):
        try:
            farm = models.Farm.objects.get(name=data)
        except models.Farm.DoesNotExist:
            raise serializers.ValidationError("Farm does not exist.")
        return farm

    def to_representation(self, value):
        return value.name


class ProjectRetrieveSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source="owner.username")
    service = serializers.ReadOnlyField(source="service.name")
    shard = serializers.ReadOnlyField(source="shard.name")
    farm = serializers.ReadOnlyField(source="farm.name")

    class Meta:
        model = models.Project
        fields = "__all__"


class ProjectCreateSerializer(serializers.ModelSerializer):
    owner = OwnerField(required=False, default=serializers.CurrentUserDefault())
    service = ServiceField()
    shard = ShardField()
    farm = FarmField(required=False)

    class Meta:
        model = models.Project
        fields = "__all__"


class ProjectUpdateSerializer(serializers.ModelSerializer):
    owner = OwnerField(required=False)
    service = ServiceField(required=False)
    shard = ShardField(required=False)
    farm = serializers.ReadOnlyField(source="farm.name")
    name = serializers.CharField(required=False)

    class Meta:
        model = models.Project
        fields = "__all__"


class LinkFarmSerializer(serializers.Serializer):
    farm = serializers.CharField()
    source = serializers.CharField()


class RegisterURLProjectSerializer(serializers.Serializer):
    url = serializers.CharField()
    probe = serializers.CharField()


class RegisterExporterProjectSerializer(serializers.Serializer):
    job = serializers.CharField()
    port = serializers.IntegerField()
    path = serializers.CharField()
    scheme = serializers.CharField()
    enabled = serializers.BooleanField()


class UpdateExporterProjectSerializer(serializers.Serializer):
    job = serializers.CharField()
    port = serializers.IntegerField()
    path = serializers.CharField()
    scheme = serializers.CharField()
    enabled = serializers.BooleanField()


class DeleteExporterProjectSerializer(serializers.Serializer):
    job = serializers.CharField()
    port = serializers.IntegerField()
    path = serializers.CharField()
    scheme = serializers.CharField()


class RegisterNotifierSerializer(serializers.Serializer):
    sender = serializers.CharField()
    value = serializers.CharField()
    alias = serializers.CharField(required=False)
    enabled = serializers.BooleanField(required=False, default=True)
