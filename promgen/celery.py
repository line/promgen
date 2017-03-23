from __future__ import absolute_import, unicode_literals

import logging
import os
import socket

import celery
import raven
from celery.signals import celeryd_after_setup
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


@celeryd_after_setup.connect
def setup_direct_queue(sender, instance, **kwargs):
    # To enable triggering config writes and reloads on a specific Prometheus server
    # we automatically create a queue for the current server that we can target from
    # our promgen.prometheus functions
    instance.app.amqp.queues.select_add(socket.gethostname())
    debug_task.apply_async(queue=socket.gethostname())
