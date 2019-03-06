# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import logging

from django import forms
from django.contrib.auth.models import User
from promgen import models
from promgen.notification import NotificationBase

logger = logging.getLogger(__name__)


def _choices():
    for user in User.objects.filter(is_active=True).order_by('username'):
        if user.first_name:
            yield (user.username, '{user.username} ({user.first_name} {user.last_name})'.format(user=user))
        elif user.email:
            yield (user.username, '{user.username} ({user.email})'.format(user=user))
        else:
            yield (user.username, user.username)


class FormUser(forms.Form):
    value = forms.ChoiceField(
        required=True,
        label='Username',
        choices=_choices
    )


class NotificationUser(NotificationBase):
    '''
    Send notification to specific user
    '''

    form = FormUser

    def splay(self, address):
        user = User.objects.get(username=address)
        for sender in models.Sender.objects.filter(obj=user):
            yield sender

    def _send(self, address, data):
        user = User.objects.get(username=address)
        for sender in models.Sender.objects.filter(obj=user):
            try:
                sender.driver._send(sender.value, data)
            except:
                logger.exception('Error sending with %s', sender)
        return True
