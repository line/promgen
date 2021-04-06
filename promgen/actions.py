from django.contrib import admin, messages

from promgen import tasks


@admin.action(description="Clear Tombstones")
def prometheus_tombstones(modeladmin, request, queryset):
    for server in queryset:
        tasks.clear_tombstones.apply_async(queue=server.host)
        messages.info(request, "Clear Tombstones on " + server.host)


@admin.action(description="Reload Configuration")
def prometheus_reload(modeladmin, request, queryset):
    for server in queryset:
        tasks.reload_prometheus.apply_async(queue=server.host)
        messages.info(request, "Reloading configuration on " + server.host)


@admin.action(description="Deploy Prometheus Targets")
def prometheus_targets(modeladmin, request, queryset):
    for server in queryset:
        tasks.write_config.apply_async(queue=server.host)
        messages.info(request, "Deploying targets to " + server.host)


@admin.action(description="Deploy Prometheus Rules")
def prometheus_rules(modeladmin, request, queryset):
    for server in queryset:
        tasks.write_rules.apply_async(queue=server.host)
        messages.info(request, "Deploying rules to " + server.host)


@admin.action(description="Deploy Prometheus Urls")
def prometheus_urls(modeladmin, request, queryset):
    for server in queryset:
        tasks.write_urls.apply_async(queue=server.host)
        messages.info(request, "Deploying urls to " + server.host)


@admin.action(description="Deploy Datasource Targets")
def shard_targets(modeladmin, request, queryset):
    for shard in queryset:
        prometheus_targets(modeladmin, request, shard.prometheus_set.all())


@admin.action(description="Deploy Datasource Rules")
def shard_rules(modeladmin, request, queryset):
    for shard in queryset:
        prometheus_rules(modeladmin, request, shard.prometheus_set.all())


@admin.action(description="Deploy Datasource Urls")
def shard_urls(modeladmin, request, queryset):
    for shard in queryset:
        prometheus_urls(modeladmin, request, shard.prometheus_set.all())
