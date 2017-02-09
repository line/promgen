import logging
import platform

from celery import group
from django.conf import settings
from django.core.management.base import BaseCommand

from promgen.celery import debug_task

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--timeout', default=10, type=int)

    def handle(self, **kwargs):
        results = []

        # Test individual Prometheus queues
        for host in settings.PROMGEN['prometheus'].get('servers'):
            queue, _ = host.split(':')
            logger.debug('Queueing URLs on %s', queue)
            results.append(debug_task.signature(queue=queue))

        # Test queue for current server
        results.append(debug_task.signature(queue=platform.node()))

        # Get the result of all of our debug tasks
        group(results)().get(timeout=kwargs['timeout'])
