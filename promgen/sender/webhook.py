import logging

from promgen.models import Project

logger = logging.getLogger(__name__)


def send(data):
    for alert in data['alerts']:
        for project in Project.objects.filter(name=alert['labels'].get('project')):
            logger.debug('Sending %s for %s', __name__, project.name)
            for sender in project.sender_set.filter(sender=__name__):
                logger.info('%s to %s', alert['labels']['alertname'], sender.value)
                break
            else:
                logger.debug('No senders configured for %s->%s', project,  __name__)
            break
        else:
            logger.debug('No senders configured for project', )
