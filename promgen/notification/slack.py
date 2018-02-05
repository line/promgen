# These sources are released under the terms of the MIT license: see LICENSE

import logging

from django import forms

from promgen import util
from promgen.notification import NotificationBase

logger = logging.getLogger(__name__)


class FormSlack(forms.Form):
    value = forms.CharField(
        required=True,
        label='Slack webhook URL'
    )
    alias = forms.CharField(
        required=False,
        help_text='Optional description to be displayed instead of the URL.'
    )

class NotificationSlack(NotificationBase):
    '''
    Send messages to slack via webhook.

    A webhook has to be configured for your workspace; you
    can set one up here:

    https://my.slack.com/services/new/incoming-webhook/

    A fitting prometheus icon can be selected from here:

    https://github.com/quintessence/slack-icons
    '''

    form = FormSlack

    def _send(self, url, data):
        if data['status'] == 'resolved':
            message = self.render('promgen/sender/slack.resolved.txt', data)
        else:
            message = self.render('promgen/sender/slack.body.txt', data)

        json = {
            'text': message,
        }

        util.post(url, json=json).raise_for_status()
