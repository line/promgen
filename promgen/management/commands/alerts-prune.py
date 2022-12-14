# Copyright (c) 2018 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

"""
Prune old alerts from Promgen's Database

Simple command to prune old alerts from Promgen's Database
based on days.

Use without arguments as dryrun or --force to execute
"""

import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from promgen import models


class Command(BaseCommand):
    help = __doc__.strip().split("\n")[0]

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=30, help="Days of alerts to delete")
        parser.add_argument(
            "--force",
            dest="dryrun",
            action="store_false",
            help="Defaults to dry run. Use to execute operation",
        )

    def success(self, message, *args):
        self.stdout.write(self.style.SUCCESS(message % args))

    def handle(self, days, dryrun, verbosity, **options):
        cutoff = timezone.now() - datetime.timedelta(days=days)

        if verbosity > 1:
            self.success("Removing alerts before %s (%d days)", cutoff, days)

        alerts = models.Alert.objects.filter(created__lt=cutoff)

        if dryrun:
            self.success("Would have removed %d alerts", alerts.count())
            return

        count, objects = alerts.delete()

        if verbosity > 1:
            self.success("Removed %d Alerts", count)
