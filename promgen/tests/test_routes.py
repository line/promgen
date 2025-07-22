# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE
from unittest import mock

import requests
from django.test import override_settings
from django.urls import reverse

from promgen import models, tests, views

TEST_SETTINGS = tests.Data("examples", "promgen.yml").yaml()
TEST_IMPORT = tests.Data("examples", "import.json").raw()
TEST_REPLACE = tests.Data("examples", "replace.json").raw()


class RouteTests(tests.PromgenTest):
    def setUp(self):
        self.user = self.force_login(username="demo")

    @override_settings(PROMGEN=TEST_SETTINGS)
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @mock.patch("promgen.signals._trigger_write_config")
    @mock.patch("promgen.tasks.reload_prometheus")
    def test_import(self, mock_write, mock_reload):
        self.add_user_permissions(
            "promgen.change_rule", "promgen.change_site", "promgen.change_exporter"
        )
        response = self.client.post(reverse("import"), {"config": TEST_IMPORT})

        self.assertRoute(response, views.Import, 302, "Redirect to imported object")
        self.assertCount(models.Service, 3, "Import one service (Fixture has two services)")
        self.assertCount(models.Project, 4, "Import two projects")
        self.assertCount(models.Exporter, 4, "Import two more exporters")
        self.assertCount(models.Host, 4, "Import three hosts (Fixture has one host)")

    @override_settings(PROMGEN=TEST_SETTINGS)
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @mock.patch("promgen.signals._trigger_write_config")
    @mock.patch("promgen.tasks.reload_prometheus")
    def test_replace(self, mock_write, mock_reload):
        self.add_user_permissions(
            "promgen.change_rule", "promgen.change_site", "promgen.change_exporter"
        )

        response = self.client.post(reverse("import"), {"config": TEST_IMPORT})
        self.assertRoute(response, views.Import, 302, "Redirect to imported object")

        response = self.client.post(reverse("import"), {"config": TEST_REPLACE})
        self.assertRoute(response, views.Import, 302, "Redirect to imported object (2)")

        self.assertCount(models.Service, 3, "Import one service (Fixture has two services)")
        self.assertCount(models.Project, 4, "Import two projects (Fixture has 2 projectsa)")
        self.assertCount(models.Exporter, 4, "Import two more exporters")
        self.assertCount(
            models.Farm, 5, "Original three farms and one new farm (fixture has one farm)"
        )
        self.assertCount(models.Host, 6, "Original 4 hosts and two new ones")

    @mock.patch("requests.get")
    def test_scrape(self, mock_get):
        shard = models.Shard.objects.create(name="test_scrape_shard")
        service = models.Service.objects.create(name="test_scrape_service", owner=self.user)
        farm = models.Farm.objects.create(name="test_scrape_farm", owner=self.user)
        farm.host_set.create(name="example.com")
        project = models.Project.objects.create(
            name="test_scrape_project", service=service, shard=shard, farm=farm, owner=self.user
        )

        # Uses the scrape target as the key, and the POST body that should
        # result in that URL
        exporters = {
            "http://example.com:8000/metrics": {
                "target": "#exporterresult",
                "job": "foo",
                "port": 8000,
                "scheme": "http",
            },
            "https://example.com:8000/foo": {
                "target": "#exporterresult",
                "job": "foo",
                "port": 8000,
                "path": "/foo",
                "scheme": "https",
            },
        }

        for url, body in exporters.items():
            response = requests.Response()
            response.url = url
            response.status_code = 200
            mock_get.return_value = response

            # For each POST body, check to see that we generate and attempt to
            # scrape the correct URL
            response = self.client.post(reverse("exporter-scrape", kwargs={"pk": project.pk}), body)
            self.assertRoute(response, views.ExporterScrape, 200)
            self.assertEqual(mock_get.call_args[0][0], url)

    def test_failed_permission(self):
        # Test for redirect
        for request in [{"viewname": "rule-new", "args": ("site", 1)}]:
            response = self.client.get(reverse(**request))
            self.assertRoute(response, views.AlertRuleRegister, 302)
            self.assertTrue(response.url.startswith("/login"))

    def test_other_routes(self):
        self.add_user_permissions("promgen.add_rule", "promgen.change_site")
        for request in [{"viewname": "rule-new", "args": ("site", 1)}]:
            response = self.client.get(reverse(**request))
            self.assertRoute(response, views.AlertRuleRegister, 200)
