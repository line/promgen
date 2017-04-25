# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import os
import shutil

import dj_database_url
from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.validators import URLValidator


class Command(BaseCommand):
    def prompt(self, prompt, *args, **kwargs):
        return input(prompt.format(*args, **kwargs))

    def write(self, fmtstr, *args, **kwargs):
        self.stdout.write(fmtstr.format(*args, **kwargs))

    def write_setting(self, key, default='', test=None):
        path = os.path.join(settings.CONFIG_DIR, key)
        if os.path.exists(path):
            self.write('Setting {} exists', key)
            return

        value = None
        if default:
            if self.prompt('Use {} for {} ? (yes/no) ', default, key).lower() == 'yes':
                value = default

        while not value:
            value = self.prompt('Please enter a value for {}: ', key).strip()
            if test:
                try:
                    test(value)
                except:
                    self.write('Invalid value {} for {}: ', value, key)
                    value = None

        self.write('Writing {} to {}', value, path)
        with open(path, 'w', encoding='utf8') as fp:
            fp.write(value)

    def handle(self, **kwargs):
        self.write('Bootstrapping Promgen')

        if not os.path.exists(settings.CONFIG_DIR):
            self.write('Creating config directory {} ', settings.CONFIG_DIR)
            os.makedirs(settings.CONFIG_DIR)

        if not os.path.exists(settings.PROMGEN_CONFIG):
            path = os.path.join(settings.BASE_DIR, 'promgen', 'tests', 'examples', 'promgen.yml')
            self.write('Creating promgen config {} from {}', settings.PROMGEN_CONFIG, path)
            shutil.copy(path, settings.PROMGEN_CONFIG)

        self.write_setting('SECRET_KEY', default=settings.SECRET_KEY)
        self.write_setting('DATABASE_URL', test=dj_database_url.parse)
        # Schemes based on list of supported brokers
        # http://docs.celeryproject.org/en/latest/getting-started/brokers/index.html
        self.write_setting('CELERY_BROKER_URL', test=URLValidator(schemes=['redis', 'amqp', 'sqs']))
