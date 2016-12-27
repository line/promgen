'''
Simple webhook bridge

Accepts alert json from Alert Manager and then POSTs individual alerts to
configured webhook destinations
'''

import logging

import requests

from promgen.celery import app as celery
from promgen.models import Sender

logger = logging.getLogger(__name__)


@celery.task
def _send(url, data):
    requests.post(url, data).raise_for_status()


def send(data):
    for alert in data['alerts']:
        project = alert['labels'].get('project')
        senders = Sender.objects.filter(sender=__name__, project__name=project)
        if senders:
            for sender in senders:
                logger.debug('Sending %s for %s', __name__, project)

                data = {
                    'prometheus': alert['generatorURL'],
                    'status': alert['status'],
                    'alertmanager': data['externalURL']
                }
                data.update(alert['labels'])
                data.update(alert['annotations'])
                _send.delay(url, data)
            return True
        else:
            logger.debug('No senders configured for %s->%s', project, __name__)
            return None


def test(target, data):
    logger.debug('Sending test message to %s', target)
    requests.post(target, data).raise_for_status()
