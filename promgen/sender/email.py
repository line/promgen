import logging

from django.conf import settings
from django.core.mail import send_mail

from promgen.models import Project

logger = logging.getLogger(__name__)


SUBJECT = '''
{alertname} {farm} {instance} {job} {_status}
'''.strip()

TEMPLATE = '''
{alertname} {farm} {instance} {job} {_status}

{summary}
{description}

Prometheus: {_prometheus}
Alert Manager: {_alertmanager}
'''.strip()


def _send(address, alert, data):

    context = {
        '_prometheus': alert['generatorURL'],
        '_status': alert['status'],
        '_alertmanager': data['externalURL']
    }
    context.update(alert['labels'])
    context.update(alert['annotations'])

    send_mail(
        SUBJECT.format(**context),
        TEMPLATE.format(**context),
        settings.PROMGEN[__name__]['sender'],
        [address]
    )


def send(data):
    for alert in data['alerts']:
        for project in Project.objects.filter(name=alert['labels'].get('project')):
            logger.debug('Sending %s for %s', __name__, project.name)
            for sender in project.sender_set.filter(sender=__name__):
                _send(sender.value, alert, data)
                break
            else:
                logger.debug('No senders configured for %s->%s', project,  __name__)
            break
        else:
            logger.debug('No senders configured for project', )
