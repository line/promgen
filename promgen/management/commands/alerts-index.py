# Copyright (c) 2020 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

from django.core.management.base import BaseCommand
from promgen import models, tasks
import time


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            dest='dryrun',
            action='store_true',
            help='show what would have been inserted',
        )

    def handle(self, dryrun, **kargs):
        for alert in models.Alert.objects.filter(alertlabel__isnull=True):
            if dryrun:
                labels = alert.json.get("commonLabels")
                for name, value in labels.items():
                    self.stderr.write("alert_id: %s, name: %s, value: %s" % (alert.pk, name, value))
                continue

            tasks.index_alert.delay(alert.pk)
            time.sleep(0.1)
