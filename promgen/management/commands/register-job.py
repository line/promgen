# Copyright (c) 2019 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

from django.core.management.base import BaseCommand, CommandError

from promgen import models, util


class Command(BaseCommand):
    def add_arguments(self, parser):
        help_text = util.HelpFor(models.Job)

        parser.add_argument("project", help="Existing Project")
        parser.add_argument("job", help=help_text.job)
        parser.add_argument("port", type=int, help=help_text.port)
        parser.add_argument("path", default="", nargs="?", help=help_text.path)
        parser.add_argument("--enabled", default=False, action="store_true", help=help_text.enabled)

    def handle(self, **kwargs):
        try:
            project = models.Project.objects.get(name=kwargs["project"])
        except models.Project.DoesNotExist:
            raise CommandError("Unable to find Project :%s" % kwargs["project"])

        job, created = models.Job.objects.get_or_create(
            project=project,
            job=kwargs["job"],
            port=kwargs["port"],
            defaults={"path": kwargs["path"], "enabled": kwargs["enabled"]},
        )
        if created:
            print("Registered job", job)
        else:
            print("Found existing job", job)
