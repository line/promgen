import logging

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from promgen.celery import app as celery
from promgen.models import Sender

logger = logging.getLogger(__name__)


@celery.task
def _send(address, alert, data):
    subject = render_to_string('promgen/sender/email.subject.txt', {
        'alert': alert,
        'externalURL': data['externalURL'],
    }).strip()

    body = render_to_string('promgen/sender/email.body.txt', {
        'alert': alert,
        'externalURL': data['externalURL'],
    }).strip()

    send_mail(
        subject,
        body,
        settings.PROMGEN[__name__]['sender'],
        [address]
    )


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
