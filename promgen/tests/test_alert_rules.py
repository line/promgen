# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

from unittest import mock

from django.core.exceptions import ValidationError
from django.test import override_settings
from django.urls import reverse

import promgen.templatetags.promgen as macro
from promgen import models, prometheus, tests, views

_RULE_V2 = """
groups:
- name: promgen.example.com
  rules:
  - alert: example-rule
    annotations:
      rule: https://promgen.example.com/rule/1
      summary: Example rule summary
    expr: up==1
    for: 1s
    labels:
      severity: high
""".lstrip().encode(
    "utf-8"
)

TEST_SETTINGS = tests.Data("examples", "promgen.yml").yaml()


class RuleTest(tests.PromgenTest):
    fixtures = ["testcases.yaml", "extras.yaml"]

    @override_settings(PROMGEN_SCHEME="https")
    @mock.patch("django.dispatch.dispatcher.Signal.send")
    def test_write_new(self, mock_post):
        result = prometheus.render_rules()
        self.assertEqual(result, _RULE_V2)

    @mock.patch("django.dispatch.dispatcher.Signal.send")
    def test_copy(self, mock_post):
        rule = models.Rule.objects.get(pk=1)
        copy = rule.copy_to(content_type="service", object_id=2)
        # Test that our copy has the same labels and annotations
        self.assertIn("severity", copy.labels)
        self.assertIn("summary", copy.annotations)

    @override_settings(PROMGEN=TEST_SETTINGS)
    @mock.patch("django.dispatch.dispatcher.Signal.send")
    def test_import_v2(self, mock_post):
        self.user = self.force_login(username="demo")
        self.add_user_permissions("promgen.change_rule", "promgen.change_site")
        response = self.client.post(
            reverse("rule-import"),
            {"rules": tests.Data("examples", "import.rule.yml").raw()},
            follow=True,
        )

        # Includes count of our setUp rule + imported rules
        self.assertRoute(response, views.RuleImport, status=200)
        self.assertCount(models.Rule, 3, "Missing Rule")

    @override_settings(PROMGEN=TEST_SETTINGS)
    @mock.patch("django.dispatch.dispatcher.Signal.send")
    def test_import_project_rule(self, mock_post):
        self.user = self.force_login(username="demo")
        self.add_user_permissions("promgen.add_rule", "promgen.change_project")

        response = self.client.post(
            reverse("rule-new", kwargs={"content_type": "project", "object_id": 1}),
            {"rules": tests.Data("examples", "import.rule.yml").raw()},
            follow=True,
        )
        self.assertRoute(response, views.ProjectDetail, status=200)
        self.assertCount(models.Rule, 3, "Missing Rule")

    @override_settings(PROMGEN=TEST_SETTINGS)
    @mock.patch("django.dispatch.dispatcher.Signal.send")
    def test_import_service_rule(self, mock_post):
        self.user = self.force_login(username="demo")
        self.add_user_permissions("promgen.add_rule", "promgen.change_service")
        response = self.client.post(
            reverse(
                "rule-new",
                kwargs={"content_type": "service", "object_id": 1},
            ),
            {"rules": tests.Data("examples", "import.rule.yml").raw()},
            follow=True,
        )
        self.assertRoute(response, views.ServiceDetail, status=200)
        self.assertCount(models.Rule, 3, "Missing Rule")

    @mock.patch("django.dispatch.dispatcher.Signal.send")
    def test_missing_permission(self, mock_post):
        self.client.post(
            reverse("rule-import"),
            {"rules": tests.Data("examples", "import.rule.yml").raw()},
        )

        # Should only be a single rule from our initial setup
        self.assertCount(models.Rule, 1, "Missing Rule")

    @mock.patch("django.dispatch.dispatcher.Signal.send")
    def test_macro(self, mock_post):
        self.site = models.Site.objects.get(pk=1)
        self.service = models.Service.objects.get(pk=1)
        self.project = models.Project.objects.get(pk=1)

        clause = "up{%s}" % macro.EXCLUSION_MACRO

        rules = {
            "common": {"assert": 'up{service!~"test-service"}'},
            "service": {"assert": 'up{service="test-service",project!~"test-project"}'},
            "project": {"assert": 'up{service="test-service",project="test-project",}'},
        }

        common_rule = models.Rule.objects.create(
            name="Common", clause=clause, duration="1s", obj=self.site
        )
        rules["common"]["model"] = models.Rule.objects.get(pk=common_rule.pk)
        service_rule = common_rule.copy_to("service", self.service.id)
        rules["service"]["model"] = models.Rule.objects.get(pk=service_rule.pk)
        project_rule = service_rule.copy_to("project", self.project.id)
        rules["project"]["model"] = models.Rule.objects.get(pk=project_rule.pk)

        for k, r in rules.items():
            self.assertEqual(macro.rulemacro(r["model"]), r["assert"], "Expansion wrong for %s" % k)

    @override_settings(PROMGEN=TEST_SETTINGS)
    @mock.patch("django.dispatch.dispatcher.Signal.send")
    def test_invalid_annotation_value(self, mock_post):
        rule = models.Rule.objects.get(pk=1)
        # $label.foo is invalid (should be $labels) so make sure we raise an exception
        rule.annotations["summary"] = "{{$label.foo}}"
        with self.assertRaises(ValidationError):
            prometheus.check_rules([rule])

    @override_settings(PROMGEN=TEST_SETTINGS)
    @mock.patch("django.dispatch.dispatcher.Signal.send")
    def test_invalid_annotation_name(self, mock_post):
        rule = models.Rule.objects.get(pk=1)
        # $label.foo is invalid (should be $labels) so make sure we raise an exception
        rule.annotations["has a space"] = "value"
        with self.assertRaises(ValidationError):
            prometheus.check_rules([rule])
