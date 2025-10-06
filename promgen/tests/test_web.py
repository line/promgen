# Copyright (c) 2022 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE
from django.urls import reverse
from guardian.shortcuts import assign_perm, remove_perm

from promgen import models, views
from promgen.tests import PromgenTest


class WebTests(PromgenTest):
    fixtures = ["testcases.yaml", "extras.yaml"]

    route_map = [
        # viewname, viewclass, extra params
        ("datasource-list", views.DatasourceList, {}),
        ("datasource-detail", views.DatasourceDetail, {"pk": 1}),
        ("service-list", views.ServiceList, {}),
        (
            "service-detail",
            views.ServiceDetail,
            {
                "pk": 1,
                "permission": "service_viewer",
                "model": models.Service,
                "permission_object_pk": 1,
            },
        ),
        (
            "project-detail",
            views.ProjectDetail,
            {
                "pk": 1,
                "permission": "project_viewer",
                "model": models.Project,
                "permission_object_pk": 1,
            },
        ),
        (
            "project-exporter",
            views.ExporterRegister,
            {
                "pk": 1,
                "permission": "project_editor",
                "model": models.Project,
                "permission_object_pk": 1,
            },
        ),
        (
            "project-notifier",
            views.ProjectNotifierRegister,
            {
                "pk": 1,
                "permission": "project_editor",
                "model": models.Project,
                "permission_object_pk": 1,
            },
        ),
        ("url-list", views.URLList, {}),
        ("farm-list", views.FarmList, {}),
        (
            "farm-detail",
            views.FarmDetail,
            {
                "pk": 1,
                "permission": "project_viewer",
                "model": models.Project,
                "permission_object_pk": 1,
            },
        ),
        ("host-list", views.HostList, {}),
        (
            "host-detail",
            views.HostDetail,
            {
                "slug": "example.com",
                "permission": "project_viewer",
                "model": models.Project,
                "permission_object_pk": 1,
            },
        ),
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
            permission = params.pop("permission", None)
            permission_model = params.pop("model", None)
            permission_object_pk = params.pop("permission_object_pk", None)
            if permission and permission_model and permission_object_pk:
                permission_object = permission_model.objects.get(pk=permission_object_pk)
                assign_perm(permission, self.user, permission_object)

            # By default we'll pass all params as-is to our reverse()
            # method, but we may have a few special ones (like status_code)
            # that we want to pop and handle separately
            # Default to checking for a 200 unless we need to specifically
            # check for a redirect or some other status code.
            status_code = params.pop("status_code", 200)
            with self.subTest(viewname=viewname, params=params):
                response = self.client.get(reverse(viewname, kwargs=params))
                self.assertRoute(response, viewclass, status_code)

            if permission and permission_model and permission_object_pk:
                permission_object = permission_model.objects.get(pk=permission_object_pk)
                remove_perm(permission, self.user, permission_object)
