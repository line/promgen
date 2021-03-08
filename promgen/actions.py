from django.contrib import messages

from promgen import tasks


# Borrowed from Django 3.2a
def action(function=None, *, permissions=None, description=None):
    def decorator(func):
        if permissions is not None:
            func.allowed_permissions = permissions
        if description is not None:
            func.short_description = description
        return func

    if function is None:
        return decorator
    else:
        return decorator(function)


@action(description="Clear Tombstones")
def prometheus_tombstones(modeladmin, request, queryset):
    for server in queryset:
        tasks.clear_tombstones.apply_async(queue=server.host)
        messages.info(request, "Clear Tombstones on " + server.host)


@action(description="Reload Configuration")
def prometheus_reload(modeladmin, request, queryset):
    for server in queryset:
        tasks.reload_prometheus.apply_async(queue=server.host)
        messages.info(request, "Reloading configuration on " + server.host)


@action(description="Deploy Prometheus Targets")
def prometheus_targets(modeladmin, request, queryset):
    for server in queryset:
        tasks.write_config.apply_async(queue=server.host)
        messages.info(request, "Deploying targets to " + server.host)


@action(description="Deploy Prometheus Rules")
def prometheus_rules(modeladmin, request, queryset):
    for server in queryset:
        tasks.write_rules.apply_async(queue=server.host)
        messages.info(request, "Deploying rules to " + server.host)


@action(description="Deploy Prometheus Urls")
def prometheus_urls(modeladmin, request, queryset):
    for server in queryset:
        tasks.write_urls.apply_async(queue=server.host)
        messages.info(request, "Deploying urls to " + server.host)


@action(description="Deploy Datasource Targets")
def shard_targets(modeladmin, request, queryset):
    for shard in queryset:
        prometheus_targets(modeladmin, request, shard.prometheus_set.all())


@action(description="Deploy Datasource Rules")
def shard_rules(modeladmin, request, queryset):
    for shard in queryset:
        prometheus_rules(modeladmin, request, shard.prometheus_set.all())


@action(description="Deploy Datasource Urls")
def shard_urls(modeladmin, request, queryset):
    for shard in queryset:
        prometheus_urls(modeladmin, request, shard.prometheus_set.all())
