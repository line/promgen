import logging

import requests
from django.conf import settings
from django.template.loader import render_to_string

from promgen.sender import SenderBase

logger = logging.getLogger(__name__)


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

        requests.post(url, data=params, headers=headers).raise_for_status()
        return True
