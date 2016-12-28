'''
Simple webhook bridge
Accepts alert json from Alert Manager and then POSTs individual alerts to
configured webhook destinations
'''

import logging

from promgen.celery import app as celery
from promgen.prometheus import post
from promgen.sender import SenderBase

logger = logging.getLogger(__name__)


class SenderWebhook(SenderBase):
    @celery.task
    def _send(url, alert, data):
        params = {
            'prometheus': alert['generatorURL'],
            'status': alert['status'],
            'alertmanager': data['externalURL']
        }
        params.update(alert['labels'])
        params.update(alert['annotations'])
        post(url, params)
        return True
