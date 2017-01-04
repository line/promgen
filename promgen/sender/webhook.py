'''
Simple webhook bridge
Accepts alert json from Alert Manager and then POSTs individual alerts to
configured webhook destinations
'''

import logging

from promgen.celery import wrap_send
from promgen.prometheus import post
from promgen.sender import SenderBase

logger = logging.getLogger(__name__)


@wrap_send
class SenderWebhook(SenderBase):
    def _send(self, url, alert, data):
        params = {
            'prometheus': alert['generatorURL'],
            'status': alert['status'],
            'alertmanager': data['externalURL']
        }
        params.update(alert['labels'])
        params.update(alert['annotations'])
        post(url, params)
        return True
