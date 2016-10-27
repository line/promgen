from django import forms
from django.contrib import admin
from pkg_resources import working_set

from promgen import models

admin.site.register(models.Service)
admin.site.register(models.Host)


@admin.register(models.Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'service', 'farm')


class SenderForm(forms.ModelForm):
    sender = forms.ChoiceField(choices=[
        (entry.module_name, entry.module_name) for entry in working_set.iter_entry_points('promgen.sender')
    ])

    class Meta:
        model = models.Sender
        exclude = []


@admin.register(models.Sender)
class SenderAdmin(admin.ModelAdmin):
    list_display = ('project', 'sender', 'value')
    form = SenderForm
    list_filter = ('project', 'sender')


@admin.register(models.Farm)
class FarmAdmin(admin.ModelAdmin):
    list_display = ('name',)
    list_filter = ('source',)


@admin.register(models.Exporter)
class ExporterAdmin(admin.ModelAdmin):
    list_display = ('job', 'port', 'path', 'project')
    list_filter = ('project', 'job', 'port')


@admin.register(models.Rule)
class RuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'clause', 'duration', 'labels', 'annotations', 'service')
    list_filter = ('service',)
