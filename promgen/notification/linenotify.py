# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import logging

from django import forms
from django.template.loader import render_to_string

from promgen import util
from promgen.celery import app as celery
from promgen.notification import NotificationBase

logger = logging.getLogger(__name__)


class FormLineNotify(forms.Form):
    value = forms.CharField(
        required=True,
        label='LINE Notify Token'
    )
    alias = forms.CharField(
        required=True,
        help_text='Use to hide token from being displayed'
    )


class NotificationLineNotify(NotificationBase):
    '''
    Send messages to line notify

    https://notify-bot.line.me/en/
    '''

    form = FormLineNotify

    @celery.task(bind=True)
    def _send(task, token, alert, data):
        self = NotificationLineNotify()  # Rebind self
        url = self.config('server')

        if alert['status'] == 'resolved':
            message = render_to_string('promgen/sender/linenotify.resolved.txt', {
                'alert': alert,
                'externalURL': data['externalURL'],
            }).strip()
        else:
            message = render_to_string('promgen/sender/linenotify.body.txt', {
                'alert': alert,
                'externalURL': data['externalURL'],
            }).strip()

        params = {
            'message': message,
        }

        headers = {
            'Authorization': 'Bearer %s' % token
        }

        util.post(url, data=params, headers=headers)
        return True
