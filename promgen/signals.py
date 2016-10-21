import logging

from django.db.models.signals import post_delete, post_save

from promgen import models, prometheus

logger = logging.getLogger(__name__)


def receiver(signal, senders, **kwargs):
    def _decorator(func):
        for sender in senders:
            signal.connect(func, sender=sender, **kwargs)
        return func
    return _decorator


@receiver(post_save, senders=[models.Rule])
def save_rule(sender, instance, created, **kwargs):
    if created:
        models.Audit.log('Updated %s %s' % (sender.__name__, instance))
    else:
        models.Audit.log('Created %s %s' % (sender.__name__, instance))

    logger.info('writing rules')

    prometheus.check_rules([instance])
    prometheus.write_rules()
    prometheus.reload_prometheus()


@receiver(post_save, senders=[models.Rule])
def delete_rule(sender, instance, **kwargs):
    models.Audit.log('Deleted %s %s' % (sender.__name__, instance))

    logger.info('writing rules')

    prometheus.check_rules([instance])
    prometheus.write_rules()
    prometheus.reload_prometheus()


@receiver(post_save, senders=[models.Exporter, models.Host, models.Farm, models.Project])
def write_config(sender, instance, created, **kwargs):
    if created:
        models.Audit.log('Updated %s %s' % (sender.__name__, instance))
    else:
        models.Audit.log('Created %s %s' % (sender.__name__, instance))

    logger.info('writing config')
    prometheus.write_config()
    prometheus.reload_prometheus()


@receiver(post_delete, senders=[models.Exporter, models.Host, models.Farm, models.Project, models.Service])
def delete_object(sender, instance, **kwargs):
    models.Audit.log('Deleted %s %s' % (sender.__name__, instance))
    logger.info('writing config')
    prometheus.write_config()
    prometheus.reload_prometheus()
