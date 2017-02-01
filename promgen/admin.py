from django import forms
from django.contrib import admin

from promgen import models, plugins

admin.site.register(models.Shard)
admin.site.register(models.Host)


@admin.register(models.Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'shard')
    list_filter = ('shard',)


@admin.register(models.Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'service', 'farm')


class SenderForm(forms.ModelForm):
    sender = forms.ChoiceField(choices=[
        (entry.module_name, entry.module_name) for entry in plugins.senders()
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
    list_display = ('job', 'port', 'path', 'project')
    list_filter = ('project', 'job', 'port')


@admin.register(models.URL)
class URLAdmin(admin.ModelAdmin):
    list_display = ('url', 'project')
    list_filter = ('project',)


@admin.register(models.Rule)
class RuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'clause', 'duration', 'labels', 'annotations', 'service')
    list_filter = ('service',)
