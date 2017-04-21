# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import logging

from django.core.mail import send_mail
from django.template.loader import render_to_string

from promgen.celery import app as celery
from promgen.notification import NotificationBase

logger = logging.getLogger(__name__)


class NotificationEmail(NotificationBase):
    '''
    Simple plaintext Email notification
    '''

    @celery.task(bind=True)
    def _send(task, address, alert, data):
        self = NotificationEmail()  # Rebind self
        subject = render_to_string('promgen/sender/email.subject.txt', {
            'alert': alert,
            'externalURL': data['externalURL'],
        }).strip()

        body = render_to_string('promgen/sender/email.body.txt', {
            'alert': alert,
            'externalURL': data['externalURL'],
        }).strip()

        send_mail(
            subject,
            body,
            self.config('sender'),
            [address]
        )
        return True
