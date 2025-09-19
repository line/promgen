import collections

from dateutil import parser
from django.db.models import prefetch_related_objects
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
    matchers = MatcherSerializer(many=True)
    startsAt = serializers.CharField(required=False)
    endsAt = serializers.CharField(required=False)
    createdBy = serializers.CharField(default="Promgen")
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
