# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import logging
import platform

from celery import group
from django.core.management.base import BaseCommand

from promgen import models
from promgen.celery import debug_task

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--timeout', default=10, type=int)

    def handle(self, **kwargs):
        results = []

        # Test individual Prometheus queues
        for server in models.Prometheus.objects.all():
            logger.info('Testing queue on %s', server.host)
            results.append(debug_task.signature(queue=server.host))

        # Test queue for current server
        results.append(debug_task.signature(queue=platform.node()))

        # Get the result of all of our debug tasks
        group(results)().get(timeout=kwargs['timeout'])
