import logging

import requests

from promgen.models import Project, Setting

TEMPLATE = '''
{alertname} {farm} {instance} {job} {_status}

{summary}
{description}

Prometheus: {_prometheus}
Alert Manager: {_alertmanager}
'''.strip()


logger = logging.getLogger(__name__)


def _send(channel, message, color):
    url, _ = Setting.objects.get_or_create(
        key=__name__,
        defaults={'value':'http://ikachan.example/notice'}
    )

    params = {
        'channel': channel,
        'message': message,
    }

    if color is not None:
        params['color'] = color
    requests.post(url.value, params).raise_for_status()


def send(data):
    for alert in data['alerts']:
        for project in Project.objects.filter(name=alert['labels'].get('project')):
            logger.debug('Sending %s for %s', __name__, project.name)
            for sender in project.sender_set.filter(sender=__name__):
                color = 'green' if alert['status'] == 'resolved' else 'red'

                params = {
                    '_prometheus': alert['generatorURL'],
                    '_status': alert['status'],
                    '_alertmanager': data['externalURL']
                }
                params.update(alert['labels'])
                params.update(alert['annotations'])
                message = TEMPLATE.format(**params)

                _send(sender.value, message, color)
                break
            else:
                logger.debug('No senders configured for %s->%s', project,  __name__)
            break
        else:
            logger.debug('No senders configured for project', )
