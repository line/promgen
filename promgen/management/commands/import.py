import json

from django.core.management.base import BaseCommand

from promgen import prometheus


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('target_file')

    def handle(self, target_file, **kwargs):
        config = json.load(open(target_file))
        prometheus.import_config(config)
