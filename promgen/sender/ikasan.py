'''
Ikasan Hipchat bridge

https://github.com/studio3104/ikasan
'''

import logging

import requests
from django.conf import settings
from django.template.loader import render_to_string

from promgen.models import Sender

logger = logging.getLogger(__name__)


def _send(channel, alert, data, color):
    url = settings.PROMGEN[__name__]['server']

    message = render_to_string('promgen/sender/ikasan.body.txt', {
        'alert': alert,
        'externalURL': data['externalURL'],
    }).strip()

    params = {
        'channel': channel,
        'message': message,
    }

    if color is not None:
        params['color'] = color
    requests.post(url, params).raise_for_status()


def test(target, data):
    logger.debug('Sending test message to %s', target)
    _send(target, data, {'externalURL': ''}, 'yellow')


def send(data):
    for alert in data['alerts']:
        project = alert['labels'].get('project')
        senders = Sender.objects.filter(sender=__name__, project__name=project)
        if senders:
            for sender in senders:
                logger.debug('Sending %s for %s', __name__, project)
                color = 'green' if alert['status'] == 'resolved' else 'red'
                _send(sender.value, alert, data, color)
            return True
        else:
            logger.debug('No senders configured for %s->%s', project, __name__)
            return None
