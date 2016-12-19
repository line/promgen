import json

import requests
from django.core.management.base import BaseCommand

from promgen import prometheus
from promgen.signals import write_config, write_rules, write_urls


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('target_file')

    def handle(self, target_file, **kwargs):
        if target_file.startswith('http'):
            config = requests.get(target_file).json()
        else:
            config = json.load(open(target_file), encoding='utf8')
        prometheus.import_config(config)
        write_config.send(self, force=True)
        write_rules.send(self, force=True)
        write_urls.send(self, force=True)
