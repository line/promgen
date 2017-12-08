# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import logging

from django.conf import settings
from django.core.management.base import BaseCommand

from promgen import prometheus

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--reload', action='store_true', help='Trigger Prometheus Reload')
        parser.add_argument(
            '--format', type=int, dest='version',
            default=settings.PROMGEN['prometheus'].get('version', 1),
            help='Prometheus rule format. Defaults to promgen.yml version (%(default)s)')
        parser.add_argument(
            'out',
            nargs='?',
            help='Optionally specify an output file to use an atomic write operation'
        )

    def handle(self, **kwargs):
        if kwargs['out']:
            prometheus.write_rules(
                path=kwargs['out'],
                reload=kwargs['reload'],
                version=kwargs['version']
            )
        else:
            self.stdout.write(prometheus.render_rules(version=kwargs['version']))
