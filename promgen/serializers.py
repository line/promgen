from promgen import models, shortcuts
from rest_framework import serializers


class ShardSerializer(serializers.ModelSerializer):
    _html = serializers.SerializerMethodField()
    _services = serializers.SerializerMethodField()

    def get__html(self, obj):
        return shortcuts.resolve_domain('shard-detail', obj.id)

    def get__services(self, obj):
        return shortcuts.resolve_domain('api:shard-services', obj.name)

    class Meta:
        model = models.Shard
        exclude = ('id',)
        lookup_field = 'name'


class ServiceSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')

    _shard = serializers.SerializerMethodField()
    _projects = serializers.SerializerMethodField()
    _html = serializers.SerializerMethodField()

    def get__html(self, obj):
        return shortcuts.resolve_domain('service-detail', obj.id)

    def get__shard(self, obj):
        return shortcuts.resolve_domain('api:shard-detail', obj.shard.name)

    def get__projects(self, obj):
        return shortcuts.resolve_domain('api:service-projects', obj.name)

    class Meta:
        model = models.Service
        exclude = ('id',)
        lookup_field = 'name'


class ProjectSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')

    _html = serializers.SerializerMethodField()
    _service = serializers.SerializerMethodField()
    _shard = serializers.SerializerMethodField()

    def get__html(self, obj):
        return shortcuts.resolve_domain('project-detail', obj.id)

    def get__service(self, obj):
        return shortcuts.resolve_domain('api:service-detail', obj.service.name)

    def get__shard(self, obj):
        return shortcuts.resolve_domain('api:shard-detail', obj.service.shard.name)

    class Meta:
        model = models.Project
        exclude = ('id', 'service', 'farm')
        lookup_field = 'name'


class SenderSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')
    label = serializers.ReadOnlyField(source='show_value')

    class Meta:
        model = models.Sender
        fields = ('sender', 'owner', 'label')
