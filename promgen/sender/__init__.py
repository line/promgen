import logging

from promgen.models import Sender

logger = logging.getLogger(__name__)


class SenderBase(object):
    def __init__(self):
        # In case some of our sender plugins are not using celery,
        # We store our calling function in self.__send so that send()
        # and test() can call the correct function while leaving the
        # original function alone in case it needs to be called directly
        if hasattr(self._send, 'delay'):
            self.__send = self._send.delay
        else:
            self.__send = self._send

    def send(self, data):
        sent = 0
        for alert in data['alerts']:
            project = alert['labels'].get('project')
            for sender in Sender.objects.filter(sender=self.__module__, project__name=project):
                if self.__send(sender.value, alert, data):
                    logger.debug('Sent %s for %s', self.__module__, project)
                    sent += 1
        if sent == 0:
            logger.debug('No senders configured for %s->%s', project, self.__module__)
        return sent

    def test(self, target, alert):
        logger.debug('Sending test message to %s', target)
        self.__send(target, alert, {'externalURL': ''})
