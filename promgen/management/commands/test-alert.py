# Copyright (c) 2018 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import json
import logging

from django.core.management.base import BaseCommand
from django.test import override_settings

from promgen import models, tasks, tests


class Command(BaseCommand):
    data = tests.PromgenTest.data_json("examples", "alertmanager.json")

    def add_arguments(self, parser):
        parser.add_argument("--shard", default="Test Shard")
        parser.add_argument("--service", default=self.data["commonLabels"]["service"])
        parser.add_argument("--project", default=self.data["commonLabels"]["project"])

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def handle(self, shard, service, project, **kwargs):
        logging._handlers = []
        logging.basicConfig(level=logging.DEBUG)

        shard, _ = models.Shard.objects.get_or_create(name=shard)
        service, _ = models.Service.objects.get_or_create(name=service)
        project, _ = models.Project.objects.get_or_create(
            name=project, defaults={"shard": shard, "service": service}
        )

        alert = models.Alert.objects.create(body=json.dumps(self.data), error_count=1)

        tasks.process_alert(alert.pk)

        alert.alerterror_set.create(message="Test from CLI")
