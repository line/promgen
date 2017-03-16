import logging
from functools import wraps

from django.conf import settings
from django.core.cache import cache
from django.db.models.signals import post_delete, post_save, pre_delete
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
    that uses Django's caching system to set wheather we
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
    for server in models.Prometheus.objects.all():
        logger.info('Queueing write_config on %s', server.host)
        prometheus.write_config.apply_async(queue=server.host)


@run_once(trigger_write_rules)
def _trigger_write_rules(signal, **kwargs):
    for server in models.Prometheus.objects.all():
        logger.info('Queueing write_rules on %s', server.host)
        prometheus.write_rules.apply_async(queue=server.host)

    return True


@run_once(trigger_write_urls)
def _trigger_write_urls(signal, **kwargs):
    for server in models.Prometheus.objects.all():
        logger.info('Queueing write_urls on %s', server.host)
        prometheus.write_urls.apply_async(queue=server.host)

    return True


@multi_receiver(post_save, senders=[models.Rule, models.Exporter, models.Host, models.Farm, models.Project, models.URL])
def save_log(sender, instance, created, **kwargs):
    if created:
        models.Audit.log('Created %s %s' % (sender.__name__, instance), instance)
    else:
        models.Audit.log('Updated %s %s' % (sender.__name__, instance), instance)


@multi_receiver(post_delete, senders=[models.Rule, models.Exporter, models.Host, models.Farm, models.Project, models.URL])
def delete_log(sender, instance, **kwargs):
    models.Audit.log('Deleted %s %s' % (sender.__name__, instance))


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
    if instance.farm and instance.farm.host_set.exists() and instance.exporter_set.exists():
        trigger_write_config.send(instance)


@receiver(pre_delete, sender=models.Project)
def delete_project(sender, instance, **kwargs):
    if instance.farm and instance.farm.host_set.exists() and instance.exporter_set.exists():
        trigger_write_config.send(instance)
