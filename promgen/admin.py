# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

from django import forms
from django.contrib import admin

from promgen import models, plugins


class PrometheusInline(admin.TabularInline):
    model = models.Prometheus


@admin.register(models.Host)
class HostAdmin(admin.ModelAdmin):
    list_display = ('name', 'farm')


@admin.register(models.Shard)
class ShardAdmin(admin.ModelAdmin):
    list_display = ('name', 'url', 'proxy')
    inlines = [PrometheusInline]


@admin.register(models.Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'shard')
    list_filter = ('shard',)


@admin.register(models.Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'service', 'farm')
    list_select_related = ('service', 'farm', 'service__shard')


class SenderForm(forms.ModelForm):
    sender = forms.ChoiceField(choices=[
        (entry.module_name, entry.module_name) for entry in plugins.notifications()
    ])

    class Meta:
        model = models.Sender
        exclude = ['content_object']


@admin.register(models.Sender)
class SenderAdmin(admin.ModelAdmin):
    list_display = ('content_object', 'content_type', 'sender', 'show_value', 'owner')
    form = SenderForm
    list_filter = ('sender', 'content_type')
    list_select_related = ('content_type',)


@admin.register(models.Farm)
class FarmAdmin(admin.ModelAdmin):
    list_display = ('name',)
    list_filter = ('source',)


@admin.register(models.Exporter)
class ExporterAdmin(admin.ModelAdmin):
    list_display = ('job', 'port', 'path', 'project', 'enabled')
    list_filter = ('job', 'port',)
    readonly_fields = ('project',)


@admin.register(models.URL)
class URLAdmin(admin.ModelAdmin):
    list_display = ('url', 'project')
    list_select_related = ('project', 'project__service', 'project__service__shard')


class RuleLabelInline(admin.TabularInline):
    model = models.RuleLabel


class RuleAnnotationInline(admin.TabularInline):
    model = models.RuleAnnotation


@admin.register(models.Rule)
class RuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'clause', 'duration', 'content_object')
    list_filter = ('duration',)
    list_select_related = ('content_type',)
    inlines = [RuleLabelInline, RuleAnnotationInline]

    def get_queryset(self, request):
        qs = super(RuleAdmin, self).get_queryset(request)
        return qs.prefetch_related('content_object',)


@admin.register(models.Prometheus)
class PrometheusAdmin(admin.ModelAdmin):
    list_display = ('shard', 'host', 'port')
    list_filter = ('shard',)
