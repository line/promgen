import logging

from promgen.models import Project, Service

logger = logging.getLogger(__name__)


class SenderBase(object):
    MAPPING = [
        ('project', Project),
        ('service', Service),
    ]

    def send(self, data):
        sent = 0
        for alert in data['alerts']:
            for label, klass in self.MAPPING:
                logger.debug('Checking for %s', label)
                if label in alert['labels']:
                    logger.debug('Checking for %s %s', label, klass)
                    for obj in klass.objects.filter(name=alert['labels'][label]):
                        for sender in obj.sender.filter(sender=self.__module__):
                            logger.debug('Sending to %s', sender)
                            if self._send(sender.value, alert, data):
                                sent += 1
        if sent == 0:
            logger.debug('No senders configured for project or service')
        return sent

    def test(self, target, alert):
        logger.debug('Sending test message to %s', target)
        self._send(target, alert, {'externalURL': ''})
