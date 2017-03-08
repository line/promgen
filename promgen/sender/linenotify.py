import logging

from django.template.loader import render_to_string

from promgen import util
from promgen.celery import app as celery
from promgen.sender import SenderBase

logger = logging.getLogger(__name__)


class SenderLineNotify(SenderBase):
    '''
    Send messages to line notify
    '''
    @celery.task(bind=True)
    def _send(task, token, alert, data):
        self = SenderLineNotify()  # Rebind self
        url = self.config('server')

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
