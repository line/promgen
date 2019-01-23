# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

'''
Simple webhook bridge
Accepts alert json from Alert Manager and then POSTs individual alerts to
configured webhook destinations
'''

import logging

from django import forms

from promgen import util
from promgen.notification import NotificationBase

logger = logging.getLogger(__name__)


class FormWebhook(forms.Form):
    value = forms.URLField(
        required=True,
        label='URL'
    )


class NotificationWebhook(NotificationBase):
    '''
    Post notifications to a specific web endpoint
    '''
    form = FormWebhook

    def _send(self, url, data):
        util.post(url, json=data).raise_for_status()
