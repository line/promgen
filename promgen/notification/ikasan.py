# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import logging

from django.template.loader import render_to_string

from promgen import util
from promgen.celery import app as celery
from promgen.notification import NotificationBase

logger = logging.getLogger(__name__)


class NotificationIkasan(NotificationBase):
    '''
    Send messages to Hipchat using Ikasan Hipchat bridge

    https://github.com/studio3104/ikasan
    '''
    @celery.task(bind=True)
    def _send(task, channel, alert, data):
        self = NotificationIkasan()  # Rebind self
        url = self.config('server')

        params = {
            'channel': channel,
            'message_format': 'text',
        }

        if alert['status'] == 'resolved':
            params['color'] = 'green'
            params['message'] = render_to_string('promgen/sender/ikasan.resolved.txt', {
                'alert': alert,
                'externalURL': data['externalURL'],
            }).strip()
        else:
            params['color'] = 'red'
            params['message'] = render_to_string('promgen/sender/ikasan.body.txt', {
                'alert': alert,
                'externalURL': data['externalURL'],
            }).strip()

        util.post(url, params)
        return True
