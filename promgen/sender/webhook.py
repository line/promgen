'''
Simple webhook bridge
Accepts alert json from Alert Manager and then POSTs individual alerts to
configured webhook destinations
'''

import logging
import requests
from promgen.sender import SenderBase

logger = logging.getLogger(__name__)


class SenderWebhook(SenderBase):
    def _send(self, url, alert, data):
        body = {
            'prometheus': alert['generatorURL'],
            'status': alert['status'],
            'alertmanager': data['externalURL']
        }
        body.update(alert['labels'])
        body.update(alert['annotations'])

        requests.post(url, body).raise_for_status()
        return True
