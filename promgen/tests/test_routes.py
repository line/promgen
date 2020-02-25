# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE
from unittest import mock

import requests

from django.test import override_settings
from django.urls import reverse

from promgen import models, views, tests

TEST_SETTINGS = tests.Data('examples', 'promgen.yml').yaml()
TEST_ALERT = tests.Data('examples', 'alertmanager.json').raw()
TEST_IMPORT = tests.Data('examples', 'import.json').raw()
TEST_REPLACE = tests.Data('examples', 'replace.json').raw()


class RouteTests(tests.PromgenTest):
    longMessage = True

    @mock.patch('django.dispatch.dispatcher.Signal.send')
    def setUp(self, mock_signal):
        self.user = self.add_force_login(id=999, username="Foo")

    @override_settings(PROMGEN=TEST_SETTINGS)
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_alert(self):
        response = self.client.post(reverse('alert'), data=TEST_ALERT, content_type='application/json')
        self.assertEqual(response.status_code, 202)

    @override_settings(PROMGEN=TEST_SETTINGS)
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @mock.patch('promgen.signals._trigger_write_config')
    @mock.patch('promgen.tasks.reload_prometheus')
    def test_import(self, mock_write, mock_reload):
        self.add_user_permissions(
            "promgen.change_rule", "promgen.change_site", "promgen.change_exporter"
        )
        response = self.client.post(reverse("import"), {"config": TEST_IMPORT})

        self.assertRoute(response, views.Import, 302, "Redirect to imported object")
        self.assertCount(models.Service, 1, "Import one service")
        self.assertCount(models.Project, 2, "Import two projects")
        self.assertCount(models.Exporter, 2, "Import two exporters")
        self.assertCount(models.Host, 3, "Import three hosts")

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

        self.assertCount(models.Service, 1, "Import one service")
        self.assertCount(models.Project, 2, "Import two projects")
        self.assertCount(models.Exporter, 2, "Import two exporters")
        self.assertCount(models.Farm, 3, "Original two farms and one new farm")
        self.assertCount(models.Host, 5, "Original 3 hosts and two new ones")

    def test_service(self):
        response = self.client.get(reverse("service-list"))
        self.assertRoute(response, views.ServiceList, 200)

    def test_project(self):
        shard = models.Shard.objects.create(name='Shard Test')
        service = models.Service.objects.create(name='Service Test')
        project = models.Project.objects.create(name='Project Test', service=service, shard=shard)

        response = self.client.get(reverse("project-detail", kwargs={"pk": project.pk}))
        self.assertRoute(response, views.ProjectDetail, 200)

    def test_farms(self):
        response = self.client.get(reverse("farm-list"))
        self.assertRoute(response, views.FarmList, 200)

    def test_hosts(self):
        response = self.client.get(reverse("host-list"))
        self.assertRoute(response, views.HostList, 200)

    @mock.patch("promgen.util.get")
    def test_scrape(self, mock_get):
        farm = models.Farm.objects.create(name="test_scrape")
        farm.host_set.create(name="example.com")

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
            mock_get.return_value = response

            # For each POST body, check to see that we generate and attempt to
            # scrape the correct URL
            response = self.client.post(
                reverse("exporter-scrape", args=(farm.pk,)), body
            )
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
