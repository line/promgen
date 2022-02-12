import collections

from rest_framework import serializers
from urllib import parse as url_parse
from django.db.models import prefetch_related_objects, ObjectDoesNotExist

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


class ProjectScrapeSerializer(serializers.Serializer):
    __DEFAULT_PATH = '/metrics'
    exporter_id = serializers.IntegerField(required=False)
    scheme = serializers.CharField(required=False)
    port = serializers.IntegerField(required=False)
    path = serializers.CharField(required=False, allow_blank=True, default=__DEFAULT_PATH)
    query = serializers.DictField(required=False, default={})

    def __init__(self, project, **kwargs):
        self.__project = project
        self.__exporter = None
        super().__init__(**kwargs)

    def validate_exporter_id(self, exporter_id):
        try:
            self.__exporter = self.__project.exporter_set.filter(pk=exporter_id).get()
            return exporter_id
        except ObjectDoesNotExist:
            raise serializers.ValidationError("Exporter with id '%d' is not found" % exporter_id)

    @staticmethod
    def validate_scheme(scheme):
        if scheme not in ['http', 'https']:
            raise serializers.ValidationError('Scheme should be http or https')
        return scheme

    @staticmethod
    def validate_port(port):
        if port < 1 or port > 65535:
            raise serializers.ValidationError('Port should be greater than 0 and lower than 65536')
        return port

    def validate_path(self, path):
        return self.__DEFAULT_PATH if not path else path

    def validate(self, data):
        if self.__exporter is None:
            required_fields = ['scheme', 'port', 'path']
            for field_name in required_fields:
                if field_name not in data:
                    raise serializers.ValidationError(
                        'Either exporter_id either %s are required' % ', '.join(required_fields)
                    )
            return data
        else:
            query = {}
            for label in self.__exporter.exporterlabel_set.all().filter(name__startswith='__param_'):
                query[label.name[8:]] = label.value
            return {
                'scheme': self.__exporter.scheme,
                'port': self.__exporter.port,
                'path': self.__exporter.path,
                'query': query,
            }

    def get_scrape_urls(self):
        self.is_valid(raise_exception=True)
        urls = []
        for host in self.__project.farm.host_set.all():
            urls.append(url_parse.urlunsplit((
                self.data['scheme'],
                f"{host.name}:{self.data['port']}",
                self.data['path'],
                url_parse.urlencode(self.data['query']),
                '',  # Fragment
            )))
        return urls

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


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
