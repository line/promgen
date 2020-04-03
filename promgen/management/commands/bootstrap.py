# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import os
import shutil

from django.conf import settings
from django.core.management.base import BaseCommand

from promgen import PROMGEN_CONFIG_DIR, PROMGEN_CONFIG_FILE
from django.contrib.sites.models import Site


PROMGEN_CONFIG_DEFAULT = (
    settings.BASE_DIR / "promgen" / "tests" / "examples" / "promgen.yml"
)


class Command(BaseCommand):
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

    def site(self, **defaults):
        """
        Check our site object to ensure that we are not directed at example.com
        """
        site, created = Site.objects.get_or_create(
            pk=settings.SITE_ID, defaults=defaults,
        )
        if site.domain == "example.com":
            Site.objects.filter(pk=settings.SITE_ID).update(**defaults)
            self.warning("site {:<15} : {domain} ({name})", settings.SITE_ID, **defaults)
        else:
            self.success("site {site.pk:<15} : {site.domain} ({site.name})", site=site)

    def add_arguments(self, parser):
        parser.add_argument("--domain", default="localhost:8000")
        parser.add_argument("--name", default="Promgen")

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

        self.write("Checking environment settings", color=self.style.MIGRATE_HEADING)
        self.setting("SECRET_KEY", default=settings.SECRET_KEY)
        self.setting("DATABASE_URL")
        self.setting("CELERY_BROKER_URL")

        self.write("Checking other settings", color=self.style.MIGRATE_HEADING)
        self.site(domain=kwargs["domain"], name=kwargs["name"])
