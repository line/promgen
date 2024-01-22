# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE
import json

from django import forms
from django.contrib import admin
from django.utils.html import format_html

from promgen import actions, models, plugins


class PrometheusInline(admin.TabularInline):
    model = models.Prometheus


class FilterInline(admin.TabularInline):
    model = models.Filter


@admin.register(models.Host)
class HostAdmin(admin.ModelAdmin):
    list_display = ("name", "farm")


@admin.register(models.Shard)
class ShardAdmin(admin.ModelAdmin):
    list_display = ("name", "url", "proxy", "enabled")
    list_filter = ("proxy", "enabled")
    inlines = [PrometheusInline]
    actions = [
        actions.shard_targets,
        actions.shard_rules,
        actions.shard_urls,
    ]


@admin.register(models.Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "owner")
    list_filter = (("owner", admin.RelatedOnlyFieldListFilter),)
    list_select_related = ("owner",)


@admin.register(models.Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "shard", "service", "farm", "owner")
    list_select_related = ("service", "farm", "shard", "owner")
    list_filter = ("shard", ("owner", admin.RelatedOnlyFieldListFilter))


class SenderForm(forms.ModelForm):
    sender = forms.ChoiceField(
        choices=[(entry.module_name, entry.module_name) for entry in plugins.notifications()]
    )

    class Meta:
        model = models.Sender
        exclude = ["content_object"]


@admin.register(models.Sender)
class SenderAdmin(admin.ModelAdmin):
    list_display = ("content_object", "content_type", "sender", "show_value", "owner")
    form = SenderForm
    list_filter = ("sender", "content_type")
    list_select_related = ("content_type",)
    inlines = [FilterInline]


@admin.register(models.Farm)
class FarmAdmin(admin.ModelAdmin):
    list_display = ("name", "source")
    list_filter = ("source",)


@admin.register(models.Exporter)
class ExporterAdmin(admin.ModelAdmin):
    list_display = ("job", "port", "path", "project", "enabled")
    list_filter = ("job", "port")
    readonly_fields = ("project",)


@admin.register(models.DefaultExporter)
class DefaultExporterAdmin(admin.ModelAdmin):
    list_display = ("job", "port", "path")
    list_filter = ("job", "port")


@admin.register(models.Probe)
class ProbeAdmin(admin.ModelAdmin):
    list_display = ("module", "description")


@admin.register(models.URL)
class URLAdmin(admin.ModelAdmin):
    # Disable add permission and project editing because of the difficult UI
    # but leave support for editing url/probe through admin panel
    def has_add_permission(self, request):
        return False

    list_display = ("url", "probe", "project")
    list_filter = ("probe", ("project__service", admin.RelatedOnlyFieldListFilter))
    list_select_related = ("project", "project__service", "probe")
    readonly_fields = ("project",)


@admin.register(models.Rule)
class RuleAdmin(admin.ModelAdmin):
    list_display = ("name", "clause", "duration", "content_object")
    list_filter = ("duration",)
    list_select_related = ("content_type",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related("content_object")


@admin.register(models.Prometheus)
class PrometheusAdmin(admin.ModelAdmin):
    list_display = ("shard", "host", "port")
    list_filter = ("shard",)
    actions = [
        actions.prometheus_targets,
        actions.prometheus_rules,
        actions.prometheus_urls,
        actions.prometheus_reload,
        actions.prometheus_tombstones,
    ]


@admin.register(models.Alert)
class AlertAdmin(admin.ModelAdmin):
    def __getattr__(self, name):
        # Override __getattr__ so that we can return a label
        # for any of our special values in list_display
        def __get_label(label):
            def __wrapped(instance):
                try:
                    return instance.json["commonLabels"][label]
                except KeyError:
                    return ""

            # We give the wrapped function the same description as
            # our label so that it shows up right in the admin panel
            __wrapped.short_description = label
            return __wrapped

        if name in self.list_display:
            return __get_label(name)

    date_hierarchy = "created"
    list_display = (
        "created",
        "datasource",
        "alertname",
        "service",
        "project",
        "severity",
        "job",
    )

    fields = ("created", "_json")
    readonly_fields = ("created", "_json")
    ordering = ("-created",)

    @admin.display(description="json")
    def _json(self, instance):
        return format_html("<pre>{}</pre>", json.dumps(instance.json, indent=2))

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False
