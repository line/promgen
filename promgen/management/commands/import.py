import json

from django.core.management.base import BaseCommand
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
                defaults={'source': 'pmc'}
            )

            project, _ = models.Project.objects.get_or_create(
                name=entry['labels']['project'],
                service=service,
                defaults={'farm': farm,}
            )
            if not project.farm:
                project.farm = farm
                project.save()

            for target in entry['targets']:
                target, port = target.split(':')
                host, _ = models.Host.objects.get_or_create(
                    name=target,
                    farm_id=farm.id,
                )

            exporter = models.Exporter.objects.get_or_create(
                job=entry['labels']['job'],
                port=port,
                project=project,
                path=entry['labels'].get('__metrics_path__', '')
            )
