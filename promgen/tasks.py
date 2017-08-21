# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import json
import logging

from celery import shared_task

from promgen import plugins, prometheus, signals  # NOQA

logger = logging.getLogger(__name__)


@shared_task
def send_notification(sender, body):
    body = json.loads(body)
    logger.info('Attempting to send alert for %s', sender)
    for plugin in plugins.notifications():
        if sender == plugin.module_name:
            try:
                instance = plugin.load()()
                count = instance.send(body)
                logger.info('Sent %d alerts with %s', count, sender)
            except:
                logger.exception('Error sending message')
