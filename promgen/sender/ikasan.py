import logging

import requests
from django.conf import settings

from promgen.models import Project

TEMPLATE = '''
{alertname} {farm} {instance} {job} {_status}

{summary}
{description}

Prometheus: {_prometheus}
Alert Manager: {_alertmanager}
'''.strip()


logger = logging.getLogger(__name__)


def _send(channel, alert, data, color):
    url = settings.PROMGEN[__name__]['server']

    context = {
        '_prometheus': alert['generatorURL'],
        '_status': alert['status'],
        '_alertmanager': data['externalURL']
    }
    context.update(alert['labels'])
    context.update(alert['annotations'])
    message = TEMPLATE.format(**context)

    params = {
        'channel': channel,
        'message': message,
    }

    if color is not None:
        params['color'] = color
    requests.post(url, params).raise_for_status()


def send(data):
    for alert in data['alerts']:
        for project in Project.objects.filter(name=alert['labels'].get('project')):
            logger.debug('Sending %s for %s', __name__, project.name)
            for sender in project.sender_set.filter(sender=__name__):
                color = 'green' if alert['status'] == 'resolved' else 'red'
                _send(sender.value, alert, data, color)
                break
            else:
                logger.debug('No senders configured for %s->%s', project,  __name__)
            break
        else:
            logger.debug('No senders configured for project', )
