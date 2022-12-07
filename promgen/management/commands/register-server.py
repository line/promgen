# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

from django.core.management.base import BaseCommand

from promgen.models import Prometheus, Shard


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("shard")
        parser.add_argument("host")
        parser.add_argument("port", type=int)

    def handle(self, shard, host, port, **kwargs):
        shard, created = Shard.objects.get_or_create(name=shard)
        if created:
            self.stdout.write("Created shard " + shard.name)

        server, created = Prometheus.objects.get_or_create(
            host=host, port=port, defaults={"shard": shard}
        )
        if created:
            self.stdout.write(f"Created {server} on {shard.name}")
        else:
            old_shard = server.shard
            server.shard = shard
            server.save()
            self.stdout.write(f"Moved {server} from {old_shard.name} to {shard.name}")
