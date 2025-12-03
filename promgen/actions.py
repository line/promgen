from django.contrib import admin, messages
from django.db import transaction
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.utils.translation import gettext as _
from guardian.models import UserObjectPermission
from guardian.shortcuts import assign_perm
from social_django.models import UserSocialAuth

from promgen import models, tasks
from promgen.notification.user import NotificationUser


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


@admin.action(description="Merge selected users")
def merge_users_action(modeladmin, request, queryset):
    if "new_user_id" not in request.POST:
        return TemplateResponse(
            request,
            "promgen/user_merge.html",
            context={
                "title": _("Merge Users"),
                "users": queryset,
            },
        )

    new_user_id = int(request.POST["new_user_id"])
    new_user = queryset.get(id=new_user_id)
    old_users = queryset.exclude(id=new_user_id)
    count = old_users.count()

    merge_users(old_users, new_user)
    messages.success(request, f"Merged {count} user(s) into {new_user.username}")

    return HttpResponseRedirect(request.get_full_path())


@transaction.atomic
def merge_users(old_users, new_user):
    # Merge social auth accounts
    UserSocialAuth.objects.filter(user__in=old_users).update(user=new_user)

    # Update owner fields
    models.Sender.objects.filter(owner__in=old_users).update(owner=new_user)
    models.Project.objects.filter(owner__in=old_users).update(owner=new_user)
    models.Service.objects.filter(owner__in=old_users).update(owner=new_user)

    # Update sender value fields for notification.user type
    models.Sender.objects.filter(
        sender=NotificationUser.__module__, value__in=old_users.values_list("id", flat=True)
    ).update(value=str(new_user.id))

    # Copy group memberships and user permissions
    for old_user in old_users:
        for group in old_user.groups.all():
            new_user.groups.add(group)
        for perm in old_user.user_permissions.all():
            new_user.user_permissions.add(perm)

    # Update object permissions. If all users have many permissions on the same object, we want to
    # keep the highest level of permission to the new user. See map_obj_perm_by_perm_rank function.
    user_ids = list(old_users.values_list("id", flat=True)) + [new_user.id]

    service_perms = UserObjectPermission.objects.filter(
        user_id__in=user_ids, content_type__app_label="promgen", content_type__model="service"
    ).values("object_pk", "permission__codename")
    service_perm_map = map_obj_perm_by_perm_rank(
        service_perms,
        {"service_admin": 3, "service_editor": 2, "service_viewer": 1},
    )
    for service_id, codename in service_perm_map.items():
        assign_perm(codename, new_user, models.Service.objects.get(pk=service_id))

    project_perms = UserObjectPermission.objects.filter(
        user_id__in=user_ids, content_type__app_label="promgen", content_type__model="project"
    ).values("object_pk", "permission__codename")
    project_perm_map = map_obj_perm_by_perm_rank(
        project_perms,
        {"project_admin": 3, "project_editor": 2, "project_viewer": 1},
    )
    for project_id, codename in project_perm_map.items():
        assign_perm(codename, new_user, models.Project.objects.get(pk=project_id))

    group_perms = UserObjectPermission.objects.filter(
        user_id__in=user_ids, content_type__app_label="auth", content_type__model="group"
    ).values("object_pk", "permission__codename")
    group_perm_map = map_obj_perm_by_perm_rank(
        group_perms,
        {"group_admin": 2, "group_member": 1},
    )
    for group_id, codename in group_perm_map.items():
        assign_perm(codename, new_user, models.Group.objects.get(pk=group_id))

    # Delete the old users, related objects will be cascade deleted
    old_users.delete()


def map_obj_perm_by_perm_rank(user_obj_perms, perm_rank):
    permission_map = {}
    for perm in user_obj_perms:
        obj_id = perm["object_pk"]
        codename = perm["permission__codename"]
        if permission_map.get(obj_id, None):
            current_rank = perm_rank[permission_map[obj_id]]
            new_rank = perm_rank[codename]
            if new_rank > current_rank:
                permission_map[obj_id] = codename
        else:
            permission_map[obj_id] = codename

    return permission_map
