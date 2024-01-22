# Copyright (c) 2019 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

from django.core.management.base import BaseCommand, CommandError

from promgen import models, util


class Command(BaseCommand):
    def add_arguments(self, parser):
        help_text = util.help_text(models.Host)

        parser.add_argument(
            "project",
            type=util.cast(models.Project),
            help="Existing Project",
        )
        parser.add_argument("host", help=help_text("name"))
        # parser.add_argument("--enabled", default=False, action="store_true", help=help_text('enabled'))

    def handle(self, project, **kwargs):
        if project.farm is None:
            raise CommandError("Project currently not associated with a farm :%s" % project)

        host, created = project.farm.host_set.get_or_create(name=kwargs["host"])
        if created:
            print("Registered host", host)
        else:
            print("Found existing host", host)
