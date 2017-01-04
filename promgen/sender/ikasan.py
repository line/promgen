'''
Ikasan Hipchat bridge
https://github.com/studio3104/ikasan
'''

import logging

from django.conf import settings
from django.template.loader import render_to_string

from promgen.celery import wrap_send
from promgen.prometheus import post
from promgen.sender import SenderBase

logger = logging.getLogger(__name__)


@wrap_send
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
        post(url, params)
        return True
