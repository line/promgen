# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import logging

from promgen import plugins, prometheus  # NOQA

logger = logging.getLogger(__name__)
for plugin in plugins.notifications():
    try:
        plugin.load()
    except ImportError:
        logger.exception('Error loading %s with Celery', plugin.module_name)
