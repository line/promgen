from __future__ import absolute_import, unicode_literals

import logging
import os
import platform

from celery import Celery

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'promgen.settings')
logger = logging.getLogger(__name__)

app = Celery('promgen')

# Using a string here means the worker don't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

app.conf.task_default_queue = platform.node()

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
