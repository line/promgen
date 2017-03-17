from __future__ import absolute_import, unicode_literals

import logging
import os
import socket

import celery
import raven
from celery.signals import celeryd_init
from raven.contrib.celery import register_logger_signal, register_signal

logger = logging.getLogger(__name__)


class Celery(celery.Celery):
    def on_configure(self):
        if 'SENTRY_DSN' in os.environ:
            client = raven.Client(os.environ.get('SENTRY_DSN'))
            register_logger_signal(client)
            register_signal(client)

app = Celery('promgen')

# Using a string here means the worker don't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))


# Because of the way that celery is de-coupled, it can be quite difficult to
# get an instance of 'self' when converting a class method into a celery task.
# as a way to get around this, we can mimick a @task(bind=True) call so that we
# get a self instance to the Celery task, and then we can set a __klass__
# attribute that we can use to get to our other class functions
def wrap_send(cls):
    if hasattr(cls, '_send'):
        logger.debug('Wrapping %s', cls)
        cls._send = app.task(cls._send, bind=True, lazy=False)
        cls._send.__klass__ = cls()
    return cls


@celeryd_init.connect
def configure_workers(sender=None, conf=None, **kwargs):
    # To enable triggering config writes and reloads on a specific Prometheus server
    # we automatically create a queue for the current server that we can target from
    # our promgen.prometheus functions
    app.control.add_consumer(queue=socket.gethostname())
    debug_task.apply_async(queue=socket.gethostname())
