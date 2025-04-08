# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import json

from django.core.management.base import BaseCommand

from promgen import prometheus, util
from promgen.middleware import get_current_user
from promgen.signals import (
    trigger_write_config,
    trigger_write_rules,
    trigger_write_urls,
)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("target_file")
        parser.add_argument("replace_shard", nargs="?")

    def handle(self, target_file, replace_shard, **kwargs):
        if target_file.startswith("http"):
            config = util.get(target_file).json()
        else:
            config = json.load(open(target_file), encoding="utf8")

        imported, skipped = prometheus.import_config(config, get_current_user(), replace_shard)

        if imported:
            counters = {key: len(imported[key]) for key in imported}
            self.stdout.write(f"Imported {counters}")

        if skipped:
            counters = {key: len(skipped[key]) for key in skipped}
            self.stdout.write(f"Skipped {counters}")

        trigger_write_config.send(self, force=True)
        trigger_write_rules.send(self, force=True)
        trigger_write_urls.send(self, force=True)
