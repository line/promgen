# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import logging

from django import forms

from promgen import util, models
from promgen.notification import NotificationBase

logger = logging.getLogger(__name__)


class FormLineNotify(forms.ModelForm):
    value = forms.CharField(
        required=True,
        label='LINE Notify Token'
    )
    alias = forms.CharField(
        required=True,
        help_text='Use to hide token from being displayed'
    )
    class Meta:
        model = models.Sender
        fields = ["value", "alias"]

class NotificationLineNotify(NotificationBase):
    '''
    Send messages to line notify

    https://notify-bot.line.me/en/
    '''

    form = FormLineNotify

    def _send(self, token, data):
        url = self.config('server')

        if data['status'] == 'resolved':
            message = self.render('promgen/sender/linenotify.resolved.txt', data)
        else:
            message = self.render('promgen/sender/linenotify.body.txt', data)

        params = {
            'message': message,
        }

        headers = {
            'Authorization': 'Bearer %s' % token
        }

        util.post(url, data=params, headers=headers).raise_for_status()
