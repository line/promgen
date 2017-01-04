import logging

from django.conf import settings
from django.template.loader import render_to_string

from promgen.celery import wrap_send
from promgen.prometheus import post
from promgen.sender import SenderBase

logger = logging.getLogger(__name__)


@wrap_send
class SenderLineNotify(SenderBase):
    def _send(self, token, alert, data):
        url = settings.PROMGEN[__name__]['server']

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

        post(url, data=params, headers=headers)
        return True
