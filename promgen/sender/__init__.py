import logging

from promgen.models import Sender

logger = logging.getLogger(__name__)


class SenderBase(object):
    def send(self, data):
        sent = 0
        for alert in data['alerts']:
            project = alert['labels'].get('project')
            for sender in Sender.objects.filter(sender=self.__module__, project__name=project):
                if self._send.delay(sender.value, alert, data):
                    logger.debug('Sent %s for %s', self.__module__, project)
                    sent += 1
        if sent == 0:
            logger.debug('No senders configured for %s->%s', project, self.__module__)
        return sent

    def test(self, target, alert):
        logger.debug('Sending test message to %s', target)
        self._send.delay(target, alert, {'externalURL': ''})
