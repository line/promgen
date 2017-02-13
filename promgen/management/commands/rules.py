import logging

from django.core.management.base import BaseCommand

from promgen import models
from promgen import prometheus

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            'out',
            nargs='?',
            help='Optionally specify an output file to use an atomic write operation'
        )

    def handle(self, out, **kwargs):
        prometheus.check_rules(models.Rule.objects.all())
        if out:
            prometheus.write_rules(out, False)
        else:
            self.stdout.write(prometheus.render_rules())
