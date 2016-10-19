import requests
from promgen.models import Project

TEMPLATE = '''
{alertname} {farm} {instance} {job} {_status}

{summary}
{description}

Prometheus: {_prometheus}
Alert Manager: {_alertmanager}
'''.strip()


def _send(channel, message, color):
    url = 'http://ikachan.cub.dev.livedoor.com/notice'
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
            channel = 'alertmanager'
            color = 'green' if alert['status'] == 'resolved' else 'red'

            params = {
                '_prometheus': alert['generatorURL'],
                '_status': alert['status'],
                '_alertmanager': data['externalURL']
            }
            params.update(alert['labels'])
            params.update(alert['annotations'])
            message = TEMPLATE.format(**params)

            _send(channel, message, color)
