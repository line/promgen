import logging

import requests
from django.conf import settings

from promgen.models import Sender

TEMPLATE = '''
{alertname} {farm} {instance} {job} {_status}

{summary}
{description}

Prometheus: {_prometheus}
Alert Manager: {_alertmanager}
'''.strip()


logger = logging.getLogger(__name__)


def _send(token, alert, data):
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
        'message': message,
    }

    headers = {
        'Authorization': 'Bearer %s' % token
    }

    requests.post(url, params, headers).raise_for_status()


def send(data):
    for alert in data['alerts']:
        project = alert['labels'].get('project')
        for sender in Sender.objects.filter(sender=__name__, project__name=project):
            logger.debug('Sending %s for %s', __name__, project)
            _send(sender.value, alert, data)
            break
        else:
            logger.debug('No senders configured for %s->%s', project,  __name__)
