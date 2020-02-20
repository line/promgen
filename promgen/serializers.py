import collections

from rest_framework import serializers

from django.db.models import prefetch_related_objects

import promgen.templatetags.promgen as macro
from promgen import models, shortcuts


class WebLinkField(serializers.Field):
    def get_attribute(self, instance):
        return instance

    def to_representation(self, obj):
        return shortcuts.resolve_domain(obj.get_absolute_url())


class ShardSerializer(serializers.ModelSerializer):
    html = WebLinkField()

    class Meta:
        model = models.Shard
        exclude = ('id',)
        lookup_field = 'name'


class ServiceSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source="owner.username")
    shard = serializers.ReadOnlyField(source="shard.name")
    html = WebLinkField()

    class Meta:
        model = models.Service
        exclude = ('id',)
        lookup_field = 'name'


class ProjectSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source="owner.username")
    service = serializers.ReadOnlyField(source="service.name")
    shard = serializers.ReadOnlyField(source="service.shard.name")
    html = WebLinkField()

    class Meta:
        model = models.Project
        lookup_field = 'name'
        exclude = ("id", "farm")


class SenderSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')
    label = serializers.ReadOnlyField(source='show_value')

    class Meta:
        model = models.Sender


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
        queryset = queryset.filter(enabled=True)
        prefetch_related_objects(
            queryset,
            "content_object",
            "content_type",
            "overrides__content_object",
            "overrides__content_type",
            "ruleannotation_set",
            "rulelabel_set",
        )
        return AlertRuleList(queryset, *args, **kwargs)

    def to_representation(self, obj):
        return {
            "alert": obj.name,
            "expr": macro.rulemacro(obj),
            "for": obj.duration,
            "labels": obj.labels,
            "annotations": obj.annotations,
        }


class URLList(serializers.ListSerializer):
    def to_representation(self, data):
        labels = {}
        targets = collections.defaultdict(list)
        for item in data:
            data = self.child.to_representation(item)
            fingerprint = str(data["labels"])
            labels[fingerprint] = data["labels"]
            targets[fingerprint] += data["targets"]
        return [{"labels": labels[f], "targets": targets[f]} for f in labels]


class UrlSeralizer(serializers.ModelSerializer):
    class Meta:
        model = models.URL
        exclude = ("id",)

    @classmethod
    def many_init(cls, queryset, *args, **kwargs):
        # when rendering many items at once, we want to make sure we
        # do our prefetch operations in one go, before passing it off
        # to our custom list renderer to group things in a dictionary
        kwargs["child"] = cls()
        prefetch_related_objects(
            queryset, "project__service", "project__shard", "project", "probe"
        )
        return URLList(queryset, *args, **kwargs)

    def to_representation(self, obj):
        return {
            "labels": {
                "project": obj.project.name,
                "service": obj.project.service.name,
                "job": obj.probe.module,
                "__shard": obj.project.shard.name,
                "__param_module": obj.probe.module,
            },
            "targets": [obj.url],
        }


class TargetSeralizer(serializers.ModelSerializer):
    class Meta:
        model = models.Exporter
        exclude = ("id",)

    @classmethod
    def many_init(cls, queryset, *args, **kwargs):
        # when rendering many items at once, we want to make sure we
        # do our prefetch operations in one go, before passing it off
        # to our custom list renderer to group things in a dictionary
        kwargs["child"] = cls()
        queryset = queryset.filter(enabled=True).exclude(project__farm=None)
        prefetch_related_objects(
            queryset,
            "project__farm__host_set",
            "project__farm",
            "project__service",
            "project__shard",
            "project",
        )
        return serializers.ListSerializer(queryset, *args, **kwargs)

    def to_representation(self, exporter):
        labels = {
            "__shard": exporter.project.shard.name,
            "service": exporter.project.service.name,
            "project": exporter.project.name,
            "farm": exporter.project.farm.name,
            "__farm_source": exporter.project.farm.source,
            "job": exporter.job,
            "__scheme__": exporter.scheme,
        }

        if exporter.path:
            labels["__metrics_path__"] = exporter.path

        return {
            "labels": labels,
            "targets": [
                "{}:{}".format(host.name, exporter.port)
                for host in exporter.project.farm.host_set.all()
            ],
        }
