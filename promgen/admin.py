# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

from django import forms
from django.contrib import admin

from promgen import models, plugins

admin.site.register(models.Host)


class PrometheusInline(admin.TabularInline):
    model = models.Prometheus


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


class SenderForm(forms.ModelForm):
    sender = forms.ChoiceField(choices=[
        (entry.module_name, entry.module_name) for entry in plugins.notifications()
    ])

    class Meta:
        model = models.Sender
        exclude = ['content_object']


@admin.register(models.Sender)
class SenderAdmin(admin.ModelAdmin):
    list_display = ('content_object', 'content_type', 'sender', 'show_value')
    form = SenderForm
    list_filter = ('sender', 'content_type')


@admin.register(models.Farm)
class FarmAdmin(admin.ModelAdmin):
    list_display = ('name',)
    list_filter = ('source',)


@admin.register(models.Exporter)
class ExporterAdmin(admin.ModelAdmin):
    list_display = ('job', 'port', 'path', 'project', 'enabled')
    list_filter = ('project', 'job', 'port')


@admin.register(models.URL)
class URLAdmin(admin.ModelAdmin):
    list_display = ('url', 'project')
    list_filter = ('project',)


class RuleLabelInline(admin.TabularInline):
    model = models.RuleLabel


class RuleAnnotationInline(admin.TabularInline):
    model = models.RuleAnnotation


@admin.register(models.Rule)
class RuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'clause', 'duration', 'content_object')
    inlines = [RuleLabelInline, RuleAnnotationInline]


@admin.register(models.Prometheus)
class PrometheusAdmin(admin.ModelAdmin):
    list_display = ('shard', 'host', 'port')
    list_filter = ('shard',)
