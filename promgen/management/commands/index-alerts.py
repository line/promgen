# Copyright (c) 2020 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

from django.core.management.base import BaseCommand
from promgen import models, tasks
import time


class Command(BaseCommand):
    def handle(self, **kargs):
        for alert in models.Alert.objects.filter(alertlabel__isnull=True):
            tasks.index_alert.delay(alert.pk)
            time.sleep(0.1)
