# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import logging

from django import forms
from django.contrib.auth.models import User
from promgen import models
from promgen.notification import NotificationBase

logger = logging.getLogger(__name__)


def _choices():
    for u in User.objects.filter(is_active=True).order_by("username"):
        if u.first_name:
            yield (u.username, f"{u.username} ({u.first_name} {u.last_name})")
        elif u.email:
            yield (u.username, f"{u.username} ({u.email})")
        else:
            yield (u.username, u.username)


class FormUser(forms.Form):
    value = forms.ChoiceField(
        required=True,
        label="Username",
        choices=_choices,
    )


class NotificationUser(NotificationBase):
    """
    Send a notification to a specific user.
    """

    form = FormUser

    def splay(self, address):
        try:
            user = User.objects.get(username=address)
        except User.DoesNotExist:
            logger.error("Missing user %s", address)
        else:
            yield from models.Sender.objects.filter(obj=user)

    def _send(self, address, data):
        user = User.objects.get(username=address)
        for sender in models.Sender.objects.filter(obj=user, enabled=True):
            try:
                sender.driver._send(sender.value, data)
            except Exception:
                logger.exception("Error sending with %s", sender)
        return True
