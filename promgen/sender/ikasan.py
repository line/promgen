'''
Ikasan Hipchat bridge
https://github.com/studio3104/ikasan
'''

import logging

import requests
from django.conf import settings
from django.template.loader import render_to_string

from promgen.sender import SenderBase

logger = logging.getLogger(__name__)


class SenderIkasan(SenderBase):
    def _send(self, channel, alert, data):
        url = settings.PROMGEN[__name__]['server']
        color = 'green' if alert['status'] == 'resolved' else 'red'

        message = render_to_string('promgen/sender/ikasan.body.txt', {
            'alert': alert,
            'externalURL': data['externalURL'],
        }).strip()

        params = {
            'channel': channel,
            'message': message,
        }

        if color is not None:
            params['color'] = color
        requests.post(url, params).raise_for_status()
        return True
