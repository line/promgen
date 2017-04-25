# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class PromgenConfig(AppConfig):
    name = 'promgen'

    def ready(self):
        from promgen import signals  # NOQA
