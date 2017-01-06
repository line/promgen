import logging

from promgen.models import Project, Service

logger = logging.getLogger(__name__)


class SenderBase(object):
    MAPPING = [
        ('project', Project),
        ('service', Service),
    ]

    def _send(self, target, alert, data):
        '''
        Sender specific implmentation

        This function will receive some kind of target value, such as an email
        address or post endpoint and an individual alert combined with some
        additional alert meta data
        '''
        raise NotImplementedError()

    def send(self, data):
        '''
        Send out an alert

        This handles looping through the alerts from Alert Manager and checks
        to see if there are any notification senders configured for the
        combination of project/service and sender type.

        See tests/examples/alertmanager.json for an example payload
        '''
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
        '''
        Send out test notification

        Combine a simple test alert from our view, with the remaining required
        parameters for our sender child classes
        '''
        logger.debug('Sending test message to %s', target)
        self._send(target, alert, {'externalURL': ''})
