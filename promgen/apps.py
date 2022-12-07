# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import logging

from django.apps import AppConfig
from django.db.models.signals import post_migrate
import warnings

logger = logging.getLogger(__name__)


def default_admin(sender, interactive, **kwargs):
    # Have to import here to ensure that the apps are already registered and
    # we get a real model instead of __fake__.User
    from django.contrib.auth.models import User

    if User.objects.filter(is_superuser=True).count() == 0:
        if interactive:
            print("  Adding default admin user")
        User.objects.create_user(
            username="admin",
            password="admin",
            is_staff=True,
            is_active=True,
            is_superuser=True,
        )
        if interactive:
            print("BE SURE TO UPDATE THE PASSWORD!!!")


def default_shard(sender, apps, interactive, **kwargs):
    Shard = apps.get_model("promgen.Shard")
    if Shard.objects.count() == 0:
        if interactive:
            print("  Adding default shard")
        Shard.objects.create(
            name="Default",
            url="http://prometheus.example.com",
            proxy=True,
            enabled=True,
        )
    if Shard.objects.filter(enabled=True).count() == 0:
        warnings.warn("No shards enabled", category=RuntimeWarning)
    if Shard.objects.filter(proxy=True).count() == 0:
        warnings.warn("No proxy shards", category=RuntimeWarning)


def check_site(app_config, **kwargs):
    Site = app_config.get_model("Site")
    if Site.objects.filter(domain__in=["example.com"]).count():
        warnings.warn("Site unconfigured", category=RuntimeWarning)


class PromgenConfig(AppConfig):
    name = "promgen"
    default_auto_field = "django.db.models.AutoField"

    def ready(self):
        from promgen import checks, signals  # NOQA

        post_migrate.connect(default_shard, sender=self)
        post_migrate.connect(default_admin, sender=self)
        post_migrate.connect(check_site, sender=self)
