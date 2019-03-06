# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import collections
import logging
from django.conf import settings

from celery import shared_task
from promgen import models, plugins, prometheus, signals  # NOQA

logger = logging.getLogger(__name__)


@shared_task
def process_alert(alert_pk):
    '''
    Process alert for routing and notifications

    We load our Alert from the database and expand it to determine which labels are routable

    Next we loop through all senders configured and de-duplicate sender:target pairs before
    queing the notification to actually be sent
    '''
    alert = models.Alert.objects.get(pk=alert_pk)
    routable, data = alert.expand()

    # For any blacklisted label patterns, we delete them from the queue
    # and consider it done (do not send any notification)
    blacklist = settings.PROMGEN.get('alert_blacklist', {})
    for key in blacklist:
        logger.debug('Checking key %s', key)
        if key in data['commonLabels']:
            if data['commonLabels'][key] in blacklist[key]:
                logger.debug('Blacklisted label %s', blacklist[key])
                alert.delete()
                return

    # Now that we have our routable items, we want to check which senders are
    # configured and expand those as needed
    senders = collections.defaultdict(set)
    for label, obj in routable.items():
        logger.debug('Processing %s %s', label, obj)
        for sender in models.Sender.objects.filter(obj=obj):
            if hasattr(sender.driver, 'splay'):
                for splay in sender.driver.splay(sender.value):
                    senders[splay.sender].add(splay.value)
            else:
                senders[sender.sender].add(sender.value)

    for driver in senders:
        for target in senders[driver]:
            send_alert.delay(driver, target, data, alert.pk)


@shared_task
def send_alert(sender, target, data, alert_pk=None):
    '''
    Send alert to specific target

    alert_pk is used for debugging purposes
    '''
    logger.debug('Sending %s %s', sender, target)
    for plugin in plugins.notifications():
        if sender == plugin.module_name:
            instance = plugin.load()()
            instance._send(target, data)
