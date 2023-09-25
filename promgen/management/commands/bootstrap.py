# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import os
import shutil

from django.conf import settings
from django.core.management.base import BaseCommand

from promgen import PROMGEN_CONFIG_DIR, PROMGEN_CONFIG_FILE

PROMGEN_CONFIG_DEFAULT = settings.BASE_DIR / "promgen" / "tests" / "examples" / "promgen.yml"


class Command(BaseCommand):
    # We manually run the system checks at the end
    requires_system_checks = False

    def prompt(self, prompt, *args, **kwargs):
        return input(prompt.format(*args, **kwargs))

    def write(self, str, color):
        self.stdout.write(color(str))

    def success(self, fmtstr, *args, **kwargs):
        self.write(fmtstr.format(*args, **kwargs), color=self.style.SUCCESS)

    def warning(self, fmtstr, *args, **kwargs):
        self.write(fmtstr.format(*args, **kwargs), color=self.style.WARNING)

    def setting(self, key, default=None, value=None):
        path = PROMGEN_CONFIG_DIR / key
        if path.exists():
            self.success("{:20} : {}", key, os.environ[key])
            return

        if default:
            if self.prompt("Use {} for {} ? (yes/no) ", default, key).lower() == "yes":
                value = default

        while not value:
            value = self.prompt("Please enter a value for {}: ", key).strip()

        self.warning("{:20} : {}", key, value)
        with path.open("w", encoding="utf8") as fp:
            fp.write(value)

    def handle(self, **kwargs):
        self.write("Bootstrapping Promgen", color=self.style.MIGRATE_HEADING)

        if not PROMGEN_CONFIG_DIR.exists():
            self.warning("Config {} Created", PROMGEN_CONFIG_DIR)
            os.makedirs(PROMGEN_CONFIG_DIR)

        if not PROMGEN_CONFIG_FILE.exists():
            self.warning(
                "Creating promgen config {} from {}",
                PROMGEN_CONFIG_FILE,
                PROMGEN_CONFIG_DEFAULT,
            )
            shutil.copy(PROMGEN_CONFIG_DEFAULT, PROMGEN_CONFIG_FILE)
        else:
            self.success("Config {} Exists", PROMGEN_CONFIG_FILE)
