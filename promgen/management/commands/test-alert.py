# Copyright (c) 2018 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import json
import logging

from django.core.management.base import BaseCommand
from django.test import override_settings
from promgen import models, tasks, tests


class Command(BaseCommand):
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def handle(self, **kwargs):
        logging._handlers = []
        logging.basicConfig(level=logging.DEBUG)

        data = tests.PromgenTest.data_json('examples', 'alertmanager.json')

        shard, _ = models.Shard.objects.get_or_create(name='Shard Test')
        service, _ = models.Service.objects.get_or_create(
            shard=shard, name=data['commonLabels']['service']
        )
        project, _ = models.Project.objects.get_or_create(
            service=service, name=data['commonLabels']['project']
        )

        alert = models.Alert.objects.create(
            body=json.dumps(data)
        )
        tasks.process_alert(alert.pk)
