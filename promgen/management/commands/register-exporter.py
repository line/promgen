# Copyright (c) 2018 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

from django.core.management.base import BaseCommand

from promgen.models import DefaultExporter


class Command(BaseCommand):
    help = """Register default exporter from the commandline"""

    # This is intended to be used from a configuration management tool
    # where there may already be a port mapping that we want to import
    # into Promgen

    def add_arguments(self, parser):
        parser.add_argument("job")
        parser.add_argument("port", type=int)
        parser.add_argument("path", nargs="?", default="")

    def handle(self, job, port, path, **kargs):
        exporter, created = DefaultExporter.objects.get_or_create(
            job=job, port=port, path=path
        )
        if created:
            self.stdout.write("Created {}".format(exporter))
        else:
            self.stdout.write("Already exists {}".format(exporter))
