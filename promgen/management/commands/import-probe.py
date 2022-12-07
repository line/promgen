# Copyright (c) 2019 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import argparse
import logging
import sys

import yaml

from django.core import exceptions
from django.core.management.base import BaseCommand

from promgen import models

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Import http probes from blackbox_exporter configuration"
    field = models.Probe._meta.get_field("description")

    # Reuse input validation from Django's createsuperuser
    def get_input_data(self, field, message, default=None):
        raw_value = input(message)
        if default and raw_value == "":
            raw_value = default
        try:
            val = field.clean(raw_value, None)
        except exceptions.ValidationError as e:
            self.stderr.write("Error: %s" % "; ".join(e.messages))
            val = None

        return val

    def add_arguments(self, parser):
        parser.add_argument(
            "config",
            help="Path to blackbox-exporter configuration",
            type=argparse.FileType("r"),
            default=sys.stdin,
        )

    def handle(self, config, verbosity, **kwargs):
        logging.root.setLevel(
            {
                0: logging.ERROR,
                1: logging.WARNING,
                2: logging.INFO,
                3: logging.DEBUG,
            }.get(verbosity)
        )
        try:
            config = yaml.safe_load(config)

            # See online example for file format
            # https://github.com/prometheus/blackbox_exporter/blob/master/example.yml

            for name, module in config.get("modules", {}).items():
                if module["prober"] != "http":
                    logger.debug("Skipping non HTTP: %s %s", name, module["prober"])
                    continue

                m, created = models.Probe.objects.get_or_create(module=name)

                if created:
                    while m.description == "":
                        m.description = self.get_input_data(
                            self.field, "Please enter description for %s: " % name
                        )
                    m.save(update_fields=["description"])
                    self.stdout.write("Added probe %s" % m)
        except KeyboardInterrupt:
            self.stderr.write("\nOperation cancelled.")
            sys.exit(1)
