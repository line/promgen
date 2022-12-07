# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

from unittest import mock

from promgen import models, tests


class SignalTest(tests.PromgenTest):
    @mock.patch("promgen.models.Audit.log")
    @mock.patch("promgen.signals.trigger_write_config.send")
    def test_write_signal(self, write_mock, log_mock):
        # Create a test farm
        farm = models.Farm.objects.create(name="farm")
        models.Host.objects.create(name="Host", farm=farm)
        # Create a new project or testing
        project = models.Project.objects.create(name="Project", service_id=1, farm=farm, shard_id=1)
        e1 = models.Exporter.objects.create(
            job="Exporter 1",
            port=1234,
            project=project,
        )

        e2 = models.Exporter.objects.create(
            job="Exporter 2",
            port=1234,
            project=project,
        )

        # Should be called once for each created exporter
        self.assertEqual(write_mock.call_count, 2, "Two write calls")
        write_mock.assert_has_calls([mock.call(e1), mock.call(e2)])

    @mock.patch("promgen.models.Audit.log")
    @mock.patch("promgen.signals.trigger_write_config.send")
    def test_write_and_delete(self, write_mock, log_mock):
        # Create a test farm
        farm = models.Farm.objects.create(name="farm")
        models.Host.objects.create(name="Host", farm=farm)

        project = models.Project.objects.create(name="Project", service_id=1, farm=farm, shard_id=1)
        # Farm but no exporters so no call
        self.assertEqual(write_mock.call_count, 0, "Should not be called without exporters")

        models.Exporter.objects.create(
            job="Exporter 1",
            port=1234,
            project=project,
        )
        # Create an exporter so our call should be 1
        self.assertEqual(write_mock.call_count, 1, "Should be called after creating exporter")

        farm.delete()
        # Deleting our farm will call pre_delete on Farm and post_save on project
        self.assertEqual(write_mock.call_count, 3, "Should be called after deleting farm")

        models.Exporter.objects.create(
            job="Exporter 2",
            port=1234,
            project=project,
        )
        # Deleting our farm means our config is inactive, so no additional calls
        # from creating exporter
        self.assertEqual(
            write_mock.call_count,
            3,
            "No farms, so should not be called after deleting exporter",
        )
