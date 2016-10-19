import json

from django.core.management.base import BaseCommand, CommandError
from promgen import models


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('target_file')

    def handle(self, target_file, **kwargs):
        config = json.load(open(target_file))
        for entry in config:
            service, _ = models.Service.objects.get_or_create(
                name=entry['labels']['service'],
            )

            farm, _ = models.Farm.objects.get_or_create(
                name=entry['labels']['farm'],
                defaults={'source': 'DB'}
            )

            project, _ = models.Project.objects.get_or_create(
                name=entry['labels']['project'],
                service=service,
                farm=farm,
            )

            for target in entry['targets']:
                target, port = target.split(':')
                host, _ = models.Host.objects.get_or_create(
                    name=target,
                    defaults={'farm': farm}
                )

            exporter = models.Exporter.objects.get_or_create(
                job=entry['labels']['job'],
                port=port,
                project=project,
            )
