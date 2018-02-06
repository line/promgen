# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import logging

from django.apps import AppConfig
from django.db.models.signals import post_migrate

logger = logging.getLogger(__name__)


def default_shard(sender, interactive, **kwargs):
    # Have to import here to ensure that the apps are already registered and
    # we get a real model instead of __fake__.User
    from django.contrib.auth.models import User
    if User.objects.filter(is_superuser=True).count() == 0:
        if interactive:
            print('  Adding default admin user')
        User.objects.create_user(
            username='admin',
            password='admin',
            is_staff=True,
            is_active=True,
            is_superuser=True,
        )
        if interactive:
            print('BE SURE TO UPDATE THE PASSWORD!!!')


def default_admin(sender, apps, interactive, **kwargs):
    Shard = apps.get_model('promgen.Shard')
    if Shard.objects.count() == 0:
        if interactive:
            print('  Adding default shard')
        Shard.objects.create(
            name='Default',
            url='http://prometheus.example.com',
            proxy=True,
        )


class PromgenConfig(AppConfig):
    name = 'promgen'

    def ready(self):
        from promgen import signals  # NOQA
        post_migrate.connect(default_shard, sender=self)
        post_migrate.connect(default_admin, sender=self)
