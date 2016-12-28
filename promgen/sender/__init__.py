import logging

from promgen.models import Project, Service

logger = logging.getLogger(__name__)


class SenderBase(object):
    def send(self, data):
        for alert in data['alerts']:
            if 'project' in alert['labels']:
                sent = 0
                for project in Project.objects.filter(name=alert['labels']['project']):
                    for sender in project.sender.all():
                        if self._send(sender.value, alert, data):
                            sent += 1
            if 'service' in alert['labels']:
                for service in Service.objects.filter(name=alert['labels']['service']):
                    for sender in service.sender.all():
                        if self._send(sender.value, alert, data):
                            sent += 1
        if sent == 0:
            logger.debug('No senders configured for project or service %s', alert['labels']['project'])
        return sent

    def test(self, target, alert):
        logger.debug('Sending test message to %s', target)
        self._send(target, alert, {'externalURL': ''})
