import logging

from django.core.management.base import BaseCommand

from promgen import prometheus

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, **kwargs):
        print prometheus.render_config()
