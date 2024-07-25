# Copyright (c) 2019 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

from unittest import mock

from django.core import management
from django.core.management.base import CommandError

from promgen import models
from promgen.tests import PromgenTest


class CLITests(PromgenTest):
    fixtures = ["testcases.yaml", "extras.yaml"]

    @mock.patch("promgen.signals._trigger_write_config")
    def test_register_job(self, mock_signal):
        # Assert when project doesn't exist
        with self.assertRaises(CommandError):
            management.call_command("register-job", "missing-project", "example", 1234)

        management.call_command("register-job", "test-project", "example", 1234)

        # Ensure the jobs we expect exist
        self.assertCount(models.Exporter, 3, "Import a new exporter")

        # Registering the same job again shouldn't change our count
        management.call_command("register-job", "test-project", "example", 1234)
        self.assertCount(models.Exporter, 3, "Import additional exporter")

        # But registering a new one will
        management.call_command("register-job", "test-project", "example", 4321)
        self.assertCount(models.Exporter, 4, 'Import additional exporter')

    @mock.patch("promgen.signals._trigger_write_config")
    def test_register_host(self, mock_signal):
        # Assert when project doesn't exist
        with self.assertRaises(CommandError):
            management.call_command("register-host", "missing-project", "cli.example.com")

        project = models.Project.objects.create(name="cli-project", service_id=1, shard_id=1)

        # Still assert an error if there is no Farm
        with self.assertRaises(CommandError):
            management.call_command("register-host", "cli-project", "cli.example.com")

        # Register farm and finally register host
        project.farm = models.Farm.objects.create(name="cli-farm")
        project.save()
        management.call_command("register-host", "cli-project", "cli.example.com")
        self.assertCount(models.Host, 2, "Should be a new host registered (1 host from fixture)")
