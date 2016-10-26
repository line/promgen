import logging
from functools import wraps

from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import Signal, receiver

from promgen import models, prometheus

logger = logging.getLogger(__name__)

write_config = Signal()
write_rules = Signal()


def multi_receiver(signal, senders, **kwargs):
    def _decorator(func):
        for sender in senders:
            signal.connect(func, sender=sender, **kwargs)
        return func
    return _decorator


def run_once(func):
    @wraps(func)
    def _wrapper(*args, **kwargs):
        key = '{}.{}'.format(func.__module__, func.__name__)
        if 'force' in kwargs:
            logger.debug('Running %s for %s', key, kwargs['sender'])
            kwargs.pop('force')
            if cache.get(key):
                cache.delete(key)
                return func(*args, **kwargs)
        else:
            logger.debug('Queueing %s for %s', key, kwargs['sender'])
            cache.set(key, 1)
    return _wrapper


@receiver(write_config)
@run_once
def _write_config(signal, **kwargs):
    prometheus.write_config()
    prometheus.reload_prometheus()
    return True


@receiver(write_rules)
@run_once
def _write_rules(signal, **kwargs):
    prometheus.write_rules()
    prometheus.reload_prometheus()
    return True


@multi_receiver(post_save, senders=[models.Rule, models.Exporter, models.Host, models.Farm, models.Project])
def save_log(sender, instance, created, **kwargs):
    if created:
        models.Audit.log('Updated %s %s' % (sender.__name__, instance))
    else:
        models.Audit.log('Created %s %s' % (sender.__name__, instance))


@multi_receiver(post_delete, senders=[models.Rule, models.Exporter, models.Host, models.Farm, models.Project])
def delete_log(sender, instance, **kwargs):
    models.Audit.log('Deleted %s %s' % (sender.__name__, instance))


@receiver(post_save, sender=models.Rule)
def save_rule(sender, instance, **kwargs):
    prometheus.check_rules([instance])
    write_rules.send(instance)


@receiver(post_delete, sender=models.Rule)
def delete_rule(sender, instance, **kwargs):
    write_rules.send(instance)


@receiver(post_save, sender=models.Host)
def save_host(sender, instance, **kwargs):
    '''Only trigger write if parent project also has exporters'''
    for project in instance.farm.project_set.all():
        if project.exporter_set:
            write_config.send(instance)


@receiver(post_delete, sender=models.Host)
def delete_host(sender, instance, **kwargs):
    '''Only trigger write if parent project also has exporters'''
    for project in instance.farm.project_set.all():
        if project.exporter_set:
            write_config.send(instance)


@receiver(post_save, sender=models.Exporter)
def save_exporter(sender, instance, **kwargs):
    '''Only trigger write if parent project also has hosts'''
    if instance.project.farm:
        if instance.project.farm.host_set.exists():
            write_config.send(instance)


@receiver(post_delete, sender=models.Exporter)
def delete_exporter(sender, instance, **kwargs):
    '''Only trigger write if parent project also has hosts'''
    if instance.project.farm:
        if instance.project.farm.host_set.exists():
            write_config.send(instance)


@receiver(post_save, sender=models.Project)
def save_project(sender, instance, update_fields, **kwargs):
    if instance.farm and instance.farm.host_set.exists() and instance.exporter_set.exists():
        write_config.send(instance)


@receiver(post_delete, sender=models.Project)
def delete_project(sender, instance, **kwargs):
    if instance.farm and instance.farm.host_set.exists() and instance.exporter_set.exists():
        write_config.send(instance)
