import logging

from promgen.models import Project

logger = logging.getLogger(__name__)


def send(data):
    for alert in data['alerts']:
        for project in Project.objects.filter(name=alert['labels'].get('project')):
            logger.info('Stub logging for %s', alert['labels']['alertname'])
