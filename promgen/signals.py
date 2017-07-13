# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import logging
from functools import wraps

from django.contrib import messages
from django.core.cache import cache
from django.db.models.signals import (post_delete, post_save, pre_delete,
                                      pre_save)
from django.dispatch import Signal, receiver

from promgen import models, prometheus

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
    '''
    Run a signal only once

    Certain actions we want to run only once, at the end of
    processing so we wrap our function in a special decorator
    that uses Django's caching system to set whether we
    want to run it or not, and trigger the actual run with
    a force keyword at the end of the request when we run to run it
    '''
    def _decorator(func):
        @wraps(func)
        def _wrapper(*args, **kwargs):
            key = '{}.{}'.format(func.__module__, func.__name__)
            if 'force' in kwargs:
                logger.debug('Checking %s for %s', key, kwargs['sender'])
                kwargs.pop('force')
                if cache.get(key):
                    cache.delete(key)
                    logger.debug('Running %s for %s', key, kwargs['sender'])
                    return func(*args, **kwargs)
            else:
                logger.debug('Queueing %s for %s', key, kwargs['sender'])
                cache.set(key, 1)
        signal.connect(_wrapper)
        return _wrapper
    return _decorator


@run_once(trigger_write_config)
def _trigger_write_config(signal, **kwargs):
    targets = [server.host for server in models.Prometheus.objects.all()]
    for target in targets:
        logger.info('Queueing write_config on %s', target)
        prometheus.write_config.apply_async(queue=target)
    if 'request' in kwargs:
        messages.info(kwargs['request'], 'Updating config on {}'.format(targets))
    return True


@run_once(trigger_write_rules)
def _trigger_write_rules(signal, **kwargs):
    targets = [server.host for server in models.Prometheus.objects.all()]
    for target in targets:
        logger.info('Queueing write_rules on %s', target)
        prometheus.write_rules.apply_async(queue=target)
    if 'request' in kwargs:
        messages.info(kwargs['request'], 'Updating rules on {}'.format(targets))
    return True


@run_once(trigger_write_urls)
def _trigger_write_urls(signal, **kwargs):
    targets = [server.host for server in models.Prometheus.objects.all()]
    for target in targets:
        logger.info('Queueing write_urls on %s', target)
        prometheus.write_urls.apply_async(queue=target)
    if 'request' in kwargs:
        messages.info(kwargs['request'], 'Updating urls on {}'.format(targets))
    return True


def update_log(sender, instance, **kwargs):
    # For our update_log, we hook the pre_save signal and make sure it's an
    # existing object by checking for a primary key. We then use that to get a
    # copy of the existing object from the database so that we can show the
    # changes
    if instance.pk:
        old = sender.objects.get(pk=instance.pk)
        models.Audit.log('Updated %s %s' % (sender.__name__, instance), instance, old)
pre_save.connect(update_log, sender=models.Exporter)
pre_save.connect(update_log, sender=models.Farm)
pre_save.connect(update_log, sender=models.Host)
pre_save.connect(update_log, sender=models.Project)
pre_save.connect(update_log, sender=models.Rule)
pre_save.connect(update_log, sender=models.Service)
pre_save.connect(update_log, sender=models.URL)


def create_log(sender, instance, created, **kwargs):
    # For our create_log, we have to hook post_save to make sure we have a
    # primary key set so that we can link back to it using the ContentType
    # system.
    if created:
        models.Audit.log('Created %s %s' % (sender.__name__, instance), instance)
post_save.connect(create_log, sender=models.Exporter)
post_save.connect(create_log, sender=models.Farm)
post_save.connect(create_log, sender=models.Host)
post_save.connect(create_log, sender=models.Project)
post_save.connect(create_log, sender=models.Rule)
post_save.connect(create_log, sender=models.Service)
post_save.connect(create_log, sender=models.URL)


def delete_log(sender, instance, **kwargs):
    models.Audit.log('Deleted %s %s' % (sender.__name__, instance), instance)
post_delete.connect(delete_log, sender=models.Exporter)
post_delete.connect(delete_log, sender=models.Farm)
post_delete.connect(delete_log, sender=models.Host)
post_delete.connect(delete_log, sender=models.Project)
post_delete.connect(delete_log, sender=models.Rule)
post_delete.connect(delete_log, sender=models.Service)
post_delete.connect(delete_log, sender=models.URL)


@receiver(post_save, sender=models.Rule)
def save_rule(sender, instance, **kwargs):
    prometheus.check_rules([instance])
    trigger_write_rules.send(instance)


@receiver(post_delete, sender=models.Rule)
def delete_rule(sender, instance, **kwargs):
    trigger_write_rules.send(instance)


@receiver(post_save, sender=models.URL)
def save_url(sender, instance, **kwargs):
    trigger_write_urls.send(instance)


@receiver(post_delete, sender=models.URL)
def delete_url(sender, instance, **kwargs):
    trigger_write_urls.send(instance)


@receiver(post_save, sender=models.Host)
def save_host(sender, instance, **kwargs):
    '''Only trigger write if parent project also has exporters'''
    for project in instance.farm.project_set.all():
        if project.exporter_set:
            trigger_write_config.send(instance)


@receiver(pre_delete, sender=models.Host)
def delete_host(sender, instance, **kwargs):
    '''Only trigger write if parent project also has exporters'''
    for project in instance.farm.project_set.all():
        if project.exporter_set.exists():
            trigger_write_config.send(instance)


@receiver(pre_delete, sender=models.Farm)
def delete_farm(sender, instance, **kwargs):
    '''Only trigger write if parent project also has exporters'''
    for project in instance.project_set.all():
        trigger_write_config.send(instance)


@receiver(post_save, sender=models.Exporter)
def save_exporter(sender, instance, **kwargs):
    '''Only trigger write if parent project also has hosts'''
    if instance.project.farm:
        if instance.project.farm.host_set.exists():
            trigger_write_config.send(instance)


@receiver(pre_delete, sender=models.Exporter)
def delete_exporter(sender, instance, **kwargs):
    '''Only trigger write if parent project also has hosts'''
    if instance.project.farm:
        if instance.project.farm.host_set.exists():
            trigger_write_config.send(instance)


@receiver(post_save, sender=models.Project)
def save_project(sender, instance, **kwargs):
    logger.debug('save_project: %s', instance)
    if instance.farm and instance.farm.host_set.exists() and instance.exporter_set.exists():
        trigger_write_config.send(instance)
        return True


@receiver(pre_delete, sender=models.Project)
def delete_project(sender, instance, **kwargs):
    if instance.farm and instance.farm.host_set.exists() and instance.exporter_set.exists():
        trigger_write_config.send(instance)


@receiver(post_save, sender=models.Service)
def save_service(sender, instance, **kwargs):
    # We saving a service, we delegate the configuration reload triggering to
    # the child projects which have additional information about if we need to
    # write out our file or not. We call our save_project signal directly
    # (instead of through post_save.save) because we don't want to trigger other
    # attached signals
    logger.debug('save_service: %s', instance)
    for project in instance.project_set.prefetch_related(
            'farm',
            'farm__host_set',
            'exporter_set'):
        if save_project(sender=models.Project, instance=project):
            # If any of our save_project returns True, then we do not need to
            # check any others
            return True
