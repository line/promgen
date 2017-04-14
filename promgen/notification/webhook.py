'''
Simple webhook bridge
Accepts alert json from Alert Manager and then POSTs individual alerts to
configured webhook destinations
'''

import logging

from promgen import util
from promgen.celery import app as celery
from promgen.notification import NotificationBase

logger = logging.getLogger(__name__)


class NotificationWebhook(NotificationBase):
    @celery.task(bind=True)
    def _send(task, url, alert, data):
        params = {
            'prometheus': alert['generatorURL'],
            'status': alert['status'],
            'alertmanager': data['externalURL']
        }

        params.update(alert.get('labels', {}))
        params.update(alert.get('annotations', {}))
        util.post(url, params)
        return True
