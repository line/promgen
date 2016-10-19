from django.contrib import admin

from promgen import models

admin.site.register(models.Service)
admin.site.register(models.Host)


@admin.register(models.Setting)
class SettingAdmin(admin.ModelAdmin):
    list_display = ('key', 'value')


@admin.register(models.Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'service', 'farm')


@admin.register(models.Sender)
class SenderAdmin(admin.ModelAdmin):
    list_display = ('project', 'sender', 'value')


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
