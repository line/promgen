'''
Ikasan Hipchat bridge
https://github.com/studio3104/ikasan
'''

import logging

from django.template.loader import render_to_string

from promgen import util
from promgen.celery import app as celery
from promgen.sender import SenderBase

logger = logging.getLogger(__name__)


class SenderIkasan(SenderBase):
    @celery.task(bind=True)
    def _send(task, channel, alert, data):
        self = SenderIkasan()  # Rebind self
        url = self.config('server')
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
        util.post(url, params)
        return True
