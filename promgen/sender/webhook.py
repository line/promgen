import logging
import requests
from promgen.models import Sender

logger = logging.getLogger(__name__)


def send(data):
    for alert in data['alerts']:
        project = alert['labels'].get('project')
        for sender in Sender.objects.filter(sender=__name__, project__name=project):
            logger.debug('Sending %s for %s', __name__, project)

            data = {
                'prometheus': alert['generatorURL'],
                'status': alert['status'],
                'alertmanager': data['externalURL']
            }
            data.update(alert['labels'])
            data.update(alert['annotations'])

            requests.post(sender.value, data).raise_for_status()
            break
        else:
            logger.debug('No senders configured for %s->%s', project,  __name__)
