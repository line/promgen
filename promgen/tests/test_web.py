# Copyright (c) 2022 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE
from django.urls import reverse

from promgen import tests, views


class WebTests(tests.PromgenTest):
    fixtures = ["testcases.yaml", "extras.yaml"]

    route_map = [
        # viewname, viewclass, extra params
        ("datasource-list", views.DatasourceList, {}),
        ("datasource-detail", views.DatasourceDetail, {"pk": 1}),
        ("service-list", views.ServiceList, {}),
        ("service-detail", views.ServiceDetail, {"pk": 1}),
        ("project-detail", views.ProjectDetail, {"pk": 1}),
        ("farm-link", views.FarmLink, {"pk": 1, "source": "promgen"}),
        ("project-exporter", views.ExporterRegister, {"pk": 1}),
        ("project-notifier", views.ProjectNotifierRegister, {"pk": 1}),
        ("url-list", views.URLList, {}),
        ("farm-list", views.FarmList, {}),
        ("farm-detail", views.FarmDetail, {"pk": 1}),
        ("host-list", views.HostList, {}),
        ("host-detail", views.HostDetail, {"slug": "example.com"}),
        ("rules-list", views.RulesList, {}),
        ("rule-detail", views.RuleDetail, {"pk": 1}),
        ("audit-list", views.AuditList, {}),
        ("site-detail", views.SiteDetail, {}),
        ("profile", views.Profile, {}),
        # For this test, we're testing a non-admin user
        # so we expect this page to redirect to 302
        ("import", views.Import, {"status_code": 302}),
        ("alert-list", views.AlertList, {}),
        ("alert-detail", views.AlertDetail, {"pk": 1}),
    ]

    def setUp(self):
        self.user = self.force_login(username="demo")

    def test_routes(self):
        for viewname, viewclass, params in self.route_map:
            # By default we'll pass all params as-is to our reverse()
            # method, but we may have a few special ones (like status_code)
            # that we want to pop and handle separately
            # Default to checking for a 200 unless we need to specifically
            # check for a redirect or some other status code.
            status_code = params.pop("status_code", 200)
            with self.subTest(viewname=viewname, params=params):
                response = self.client.get(reverse(viewname, kwargs=params))
                self.assertRoute(response, viewclass, status_code)
