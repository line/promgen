# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import logging
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.db.models import Q
from django.db.models.signals import post_delete, post_save, pre_delete, pre_save
from django.dispatch import Signal, receiver
from guardian.models import GroupObjectPermission, UserObjectPermission
from guardian.shortcuts import assign_perm

from promgen import models, prometheus, tasks

logger = logging.getLogger(__name__)

trigger_write_config = Signal()
trigger_write_rules = Signal()
trigger_write_urls = Signal()
post_reload = Signal()


def multi_receiver(signal, senders, **kwargs):
    def _decorator(func):
        for sender in senders:
            signal.connect(func, sender=sender, **kwargs)
        return func

    return _decorator


def run_once(signal):
    """
    Run a signal only once

    Certain actions we want to run only once, at the end of
    processing so we wrap our function in a special decorator
    that uses Django's caching system to set whether we
    want to run it or not, and trigger the actual run with
    a force keyword at the end of the request when we run to run it
    """

    def _decorator(func):
        @wraps(func)
        def _wrapper(*args, **kwargs):
            key = f"{func.__module__}.{func.__name__}"
            if "force" in kwargs:
                logger.debug("Checking %s for %s", key, kwargs["sender"])
                kwargs.pop("force")
                if cache.get(key):
                    cache.delete(key)
                    logger.debug("Running %s for %s", key, kwargs["sender"])
                    return func(*args, **kwargs)
            else:
                logger.debug("Queueing %s for %s", key, kwargs["sender"])
                cache.set(key, 1)

        signal.connect(_wrapper)
        return _wrapper

    return _decorator


def skip_raw(func):
    """
    For many of our signals that call out to an external service, we want to skip
    it any time we have a raw object from a fixture. This decorator helps us centralize
    our check code to keep it consistent
    """

    @wraps(func)
    def _wrapper(*, raw=False, instance, **kwargs):
        if raw:
            logger.debug("Skipping %s:%s for raw %s", __name__, func.__name__, instance)
            return
        logger.debug("Running %s:%s for %s", __name__, func.__name__, instance)
        return func(raw=raw, instance=instance, **kwargs)

    return _wrapper


@run_once(trigger_write_config)
def _trigger_write_config(signal, **kwargs):
    targets = [server.host for server in models.Prometheus.objects.all()]
    for target in targets:
        logger.info("Queueing write_config on %s", target)
        tasks.write_config.apply_async(queue=target)
    if "request" in kwargs:
        messages.info(kwargs["request"], f"Updating config on {targets}")
    return True


@run_once(trigger_write_rules)
def _trigger_write_rules(signal, **kwargs):
    targets = [server.host for server in models.Prometheus.objects.all()]
    for target in targets:
        logger.info("Queueing write_rules on %s", target)
        tasks.write_rules.apply_async(queue=target)
    if "request" in kwargs:
        messages.info(kwargs["request"], f"Updating rules on {targets}")
    return True


@run_once(trigger_write_urls)
def _trigger_write_urls(signal, **kwargs):
    targets = [server.host for server in models.Prometheus.objects.all()]
    for target in targets:
        logger.info("Queueing write_urls on %s", target)
        tasks.write_urls.apply_async(queue=target)
    if "request" in kwargs:
        messages.info(kwargs["request"], f"Updating urls on {targets}")
    return True


@skip_raw
def update_log(sender, instance, **kwargs):
    # For our update_log, we hook the pre_save signal and make sure it's an
    # existing object by checking for a primary key. We then use that to get a
    # copy of the existing object from the database so that we can show the
    # changes
    if instance.pk:
        old = sender.objects.get(pk=instance.pk)
        models.Audit.log(f"Updated {sender.__name__} {instance}", instance, old)


pre_save.connect(update_log, sender=models.Exporter)
pre_save.connect(update_log, sender=models.Farm)
pre_save.connect(update_log, sender=models.Host)
pre_save.connect(update_log, sender=models.Project)
pre_save.connect(update_log, sender=models.Rule)
pre_save.connect(update_log, sender=models.Sender)
pre_save.connect(update_log, sender=models.Service)
pre_save.connect(update_log, sender=models.URL)
pre_save.connect(update_log, sender=models.Group)


@skip_raw
def create_log(sender, instance, created, **kwargs):
    # For our create_log, we have to hook post_save to make sure we have a
    # primary key set so that we can link back to it using the ContentType
    # system.
    if created:
        models.Audit.log(f"Created {sender.__name__} {instance}", instance)


post_save.connect(create_log, sender=models.Exporter)
post_save.connect(create_log, sender=models.Farm)
post_save.connect(create_log, sender=models.Host)
post_save.connect(create_log, sender=models.Project)
post_save.connect(create_log, sender=models.Rule)
post_save.connect(create_log, sender=models.Sender)
post_save.connect(create_log, sender=models.Service)
post_save.connect(create_log, sender=models.URL)
post_save.connect(create_log, sender=UserObjectPermission)
post_save.connect(create_log, sender=models.Group)


def delete_log(sender, instance, **kwargs):
    models.Audit.log(f"Deleted {sender.__name__} {instance}", instance)


post_delete.connect(delete_log, sender=models.Exporter)
post_delete.connect(delete_log, sender=models.Farm)
post_delete.connect(delete_log, sender=models.Host)
post_delete.connect(delete_log, sender=models.Project)
post_delete.connect(delete_log, sender=models.Rule)
post_delete.connect(delete_log, sender=models.Sender)
post_delete.connect(delete_log, sender=models.Service)
post_delete.connect(delete_log, sender=models.URL)
post_delete.connect(delete_log, sender=UserObjectPermission)
post_delete.connect(delete_log, sender=models.Group)


@receiver(post_save, sender=models.Rule)
@skip_raw
def save_rule(sender, instance, **kwargs):
    prometheus.check_rules([instance])
    trigger_write_rules.send(instance)


@receiver(post_delete, sender=models.Rule)
def delete_rule(sender, instance, **kwargs):
    trigger_write_rules.send(instance)


@receiver(post_save, sender=models.URL)
@skip_raw
def save_url(sender, instance, **kwargs):
    trigger_write_urls.send(instance)


@receiver(post_delete, sender=models.URL)
def delete_url(sender, instance, **kwargs):
    trigger_write_urls.send(instance)


@receiver(post_save, sender=models.Host)
@skip_raw
def save_host(sender, instance, **kwargs):
    """Only trigger write if parent project also has exporters"""
    for project in instance.farm.project_set.all():
        if project.exporter_set:
            trigger_write_config.send(instance)


@receiver(pre_delete, sender=models.Host)
def delete_host(sender, instance, **kwargs):
    """Only trigger write if parent project also has exporters"""
    for project in instance.farm.project_set.all():
        if project.exporter_set.exists():
            trigger_write_config.send(instance)


@receiver(pre_delete, sender=models.Farm)
def delete_farm(sender, instance, **kwargs):
    """Only trigger write if parent project also has exporters"""
    for project in instance.project_set.all():
        trigger_write_config.send(instance)


@receiver(post_save, sender=models.Exporter)
@skip_raw
def save_exporter(sender, instance, **kwargs):
    """Only trigger write if parent project also has hosts"""
    if instance.project.farm:
        if instance.project.farm.host_set.exists():
            trigger_write_config.send(instance)


@receiver(pre_delete, sender=models.Exporter)
def delete_exporter(sender, instance, **kwargs):
    """Only trigger write if parent project also has hosts"""
    if instance.project.farm:
        if instance.project.farm.host_set.exists():
            trigger_write_config.send(instance)


@receiver(post_save, sender=models.Project)
@skip_raw
def save_project(instance, **kwargs):
    if instance.farm and instance.farm.host_set.exists() and instance.exporter_set.exists():
        trigger_write_config.send(instance)
        return True


@receiver(pre_delete, sender=models.Project)
def delete_project(sender, instance, **kwargs):
    if instance.farm and instance.farm.host_set.exists() and instance.exporter_set.exists():
        trigger_write_config.send(instance)


@receiver(post_save, sender=models.Service)
@skip_raw
def save_service(*, sender, instance, **kwargs):
    # We saving a service, we delegate the configuration reload triggering to
    # the child projects which have additional information about if we need to
    # write out our file or not. We call our save_project signal directly
    # (instead of through post_save.save) because we don't want to trigger other
    # attached signals
    # We don't use sender here, but put it in our parameters so we don't pass
    # two sender entries to save_project
    for project in instance.project_set.prefetch_related("farm", "farm__host_set", "exporter_set"):
        if save_project(sender=models.Project, instance=project, **kwargs):
            # If any of our save_project returns True, then we do not need to
            # check any others
            return True


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
@skip_raw
def add_user_to_default_group(instance, created, **kwargs):
    # If we enabled our default group, then we want to ensure that all newly
    # created users are also added to our default group so they inherit the
    # default permissions
    if not settings.PROMGEN_DEFAULT_GROUP:
        return
    if not created:
        return

    instance.groups.add(Group.objects.get(name=settings.PROMGEN_DEFAULT_GROUP))


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
@skip_raw
def add_email_sender(instance, created, **kwargs):
    if instance.email:
        models.Sender.objects.get_or_create(
            obj=instance, sender="promgen.notification.email", value=instance.email, owner=instance
        )
    else:
        logger.warning("No email for user %s", instance)


# Not a 'real' signal but we match most of the interface for post_save
def check_user_subscription(sender, instance, created, request):
    # When a user subscribes to a notification, we want to ensure
    # they have a default notification enabled
    if instance.sender != "promgen.notification.user":
        messages.success(request, "Subscription saved")
        return

    notifiers = models.Sender.objects.filter(obj=instance.owner)
    if notifiers:
        logger.debug("Existing notifiers found")
        return

    if instance.owner.email:
        models.Sender.objects.get_or_create(
            obj=instance.owner,
            sender="promgen.notification.email",
            value=instance.owner.email,
        )
        messages.success(request, "Subscribed using %s" % (instance.owner.email))
    else:
        messages.warning(request, "No email configured")


@receiver(post_save, sender=models.Service)
@skip_raw
def add_default_service_subscription(instance, created, **kwargs):
    if created and instance.owner:
        sender, new_notifier = models.Sender.objects.get_or_create(
            obj=instance,
            sender="promgen.notification.user",
            value=instance.owner.username,
            defaults={"owner": instance.owner},
        )


@receiver(post_save, sender=models.Project)
@skip_raw
def add_default_project_subscription(instance, created, **kwargs):
    if created and instance.owner:
        sender, new_notifier = models.Sender.objects.get_or_create(
            obj=instance,
            sender="promgen.notification.user",
            value=instance.owner.username,
            defaults={"owner": instance.owner},
        )


@skip_raw
def assign_admin_to_owner(sender, instance, created, **kwargs):
    # assign the admin role to the owner of the instance when it is created
    if created and instance.owner:
        assign_perm(sender._meta.model_name + "_admin", instance.owner, instance)


post_save.connect(assign_admin_to_owner, sender=models.Service)
post_save.connect(assign_admin_to_owner, sender=models.Project)
post_save.connect(assign_admin_to_owner, sender=models.Farm)


@skip_raw
def remove_obj_perms_connected_with_user(sender, instance, **kwargs):
    filters = Q(content_type=ContentType.objects.get_for_model(instance), object_pk=instance.pk)
    UserObjectPermission.objects.filter(filters).delete()
    GroupObjectPermission.objects.filter(filters).delete()


post_delete.connect(remove_obj_perms_connected_with_user, sender=models.Service)
post_delete.connect(remove_obj_perms_connected_with_user, sender=models.Project)
post_delete.connect(remove_obj_perms_connected_with_user, sender=models.Farm)
post_delete.connect(remove_obj_perms_connected_with_user, sender=models.Group)
