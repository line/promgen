import logging

from django.conf import settings
from django.template.loader import render_to_string

from promgen.celery import app as celery
from promgen.models import Sender
from promgen.prometheus import post

logger = logging.getLogger(__name__)


@celery.task
def _send(token, alert, data):
    url = settings.PROMGEN[__name__]['server']

    message = render_to_string('promgen/sender/linenotify.body.txt', {
        'alert': alert,
        'externalURL': data['externalURL'],
    }).strip()

    params = {
        'message': message,
    }

    headers = {
        'Authorization': 'Bearer %s' % token
    }

    post(url, data=params, headers=headers)


def test(target, alert):
    logger.debug('Sending test message to %s', target)
    _send.delay(target, alert, {'externalURL': ''})


def send(data):
    for alert in data['alerts']:
        project = alert['labels'].get('project')
        senders = Sender.objects.filter(sender=__name__, project__name=project)
        if senders:
            for sender in senders:
                logger.debug('Sending %s for %s', __name__, project)
                _send.delay(sender.value, alert, data)
            return True
        else:
            logger.debug('No senders configured for %s->%s', project, __name__)
            return None
