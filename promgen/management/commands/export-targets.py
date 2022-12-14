# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import logging

from django.core.management.base import BaseCommand

from promgen import prometheus, tasks

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--reload",
            action="store_true",
            help="Trigger Prometheus Reload",
        )
        parser.add_argument(
            "--mode",
            type=lambda x: int(x, 8),
            default=0o644,
            help="Set mode for output file (default 644)",
        )
        parser.add_argument(
            "out",
            nargs="?",
            help="Optionally specify an output file to use an atomic write operation",
        )

    def handle(self, **kwargs):
        if kwargs["out"]:
            tasks.write_config(kwargs["out"], kwargs["reload"], kwargs["mode"])
        else:
            self.stdout.write(prometheus.render_config())
