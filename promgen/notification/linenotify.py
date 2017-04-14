import logging

from django.template.loader import render_to_string

from promgen import util
from promgen.celery import app as celery
from promgen.notification import NotificationBase

logger = logging.getLogger(__name__)


class NotificationLineNotify(NotificationBase):
    '''
    Send messages to line notify

    https://notify-bot.line.me/en/
    '''
    @celery.task(bind=True)
    def _send(task, token, alert, data):
        self = NotificationLineNotify()  # Rebind self
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
