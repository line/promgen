# Copyright (c) 2019 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

from unittest import mock

from django.core import management
from django.core.management.base import CommandError

from promgen import models
from promgen.tests import PromgenTest


class CLITests(PromgenTest):
    @mock.patch("django.dispatch.dispatcher.Signal.send")
    def test_register_job(self, mock_signal):
        # Assert when project doesn't exist
        with self.assertRaises(CommandError):
            management.call_command("register-job", "missing-project", "example", 1234)

        # Create a Service and Project and then try adding our job
        shard = models.Shard.objects.create(name="TestShard")
        service = models.Service.objects.create(name="TestService")
        _ = models.Project.objects.create(name="TestProject", service=service, shard=shard)
        management.call_command("register-job", "TestProject", "example", 1234)

        # Ensure the jobs we expect exist
        self.assertCount(models.Job, 1)

        # Registering the same job again shouldn't change our count
        management.call_command("register-job", "TestProject", "example", 1234)
        self.assertCount(models.Job, 1)

        # But registering a new one will
        management.call_command("register-job", "TestProject", "example", 4321)
        self.assertCount(models.Job, 2)

    @mock.patch("django.dispatch.dispatcher.Signal.send")
    def test_register_host(self, mock_signal):
        # Assert when project doesn't exist
        with self.assertRaises(CommandError):
            management.call_command("register-host", "missing-project", "example.com")

        # Create a Service and Project and then try adding our job
        shard = models.Shard.objects.create(name="TestShard")
        service = models.Service.objects.create(name="TestService")
        project = models.Project.objects.create(name="TestProject", service=service, shard=shard)

        # Still assert an error if there is no Farm
        with self.assertRaises(CommandError):
            management.call_command("register-host", "TestProject", "example.com")

        # Register farm and finally register host
        project.farm = models.Farm.objects.create(name="TestFarm")
        project.save()
        management.call_command("register-host", "TestProject", "example.com")
        self.assertCount(models.Host, 1, "Should be a single host registered")
