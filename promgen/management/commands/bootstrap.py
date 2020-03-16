# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import os
import shutil

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def prompt(self, prompt, *args, **kwargs):
        return input(prompt.format(*args, **kwargs))

    def heading(self, str):
        self.stdout.write(self.style.MIGRATE_HEADING(str))

    def write(self, fmtstr, *args, **kwargs):
        self.stdout.write(fmtstr.format(*args, **kwargs))

    def write_setting(self, key, default=None, value=None):
        path = settings.PROMGEN_CONFIG_DIR / key
        if path.exists():
            self.write("  Setting {} exists", key)
            return

        if default:
            if self.prompt("Use {} for {} ? (yes/no) ", default, key).lower() == "yes":
                value = default

        while not value:
            value = self.prompt("Please enter a value for {}: ", key).strip()

        self.write("Writing {} to {}", value, path)
        with path.open("w", encoding="utf8") as fp:
            fp.write(value)

    def handle(self, **kwargs):
        self.heading("Bootstrapping Promgen")

        if not settings.PROMGEN_CONFIG_DIR.exists():
            self.write("Creating config directory {} ", settings.PROMGEN_CONFIG_DIR)
            os.makedirs(settings.PROMGEN_CONFIG_DIR)

        if not settings.PROMGEN_CONFIG.exists():
            path = settings.BASE_DIR / "promgen" / "tests" / "examples" / "promgen.yml"
            self.write("  Creating promgen config {} from {}", settings.PROMGEN_CONFIG, path)
            shutil.copy(path, settings.PROMGEN_CONFIG)

        self.write_setting("SECRET_KEY", default=settings.SECRET_KEY)
        self.write_setting("DATABASE_URL")
        # Schemes based on list of supported brokers
        # http://docs.celeryproject.org/en/latest/getting-started/brokers/index.html
        self.write_setting("CELERY_BROKER_URL")
