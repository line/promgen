import logging

from promgen import plugins, prometheus  # NOQA

logger = logging.getLogger(__name__)
for plugin in plugins.senders():
    try:
        plugin.load()
    except ImportError:
        logger.exception('Error loading %s with Celery', plugin.module_name)
