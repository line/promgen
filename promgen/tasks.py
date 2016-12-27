import logging

import requests

from promgen import plugins, prometheus
from promgen.celery import app

logger = logging.getLogger(__name__)
for plugin in plugins.senders():
    try:
        plugin.load()
    except ImportError:
        logger.exception('Error loading %s with Celery', plugin.module_name)
