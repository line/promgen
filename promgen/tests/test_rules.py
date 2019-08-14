# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

from unittest import mock

import promgen.templatetags.promgen as macro
from promgen import models, prometheus, views
from promgen.tests import PromgenTest

from django.core.exceptions import ValidationError
from django.test import override_settings
from django.urls import reverse

_RULE_V2 = '''
groups:
- name: example.com
  rules:
  - alert: RuleName
    annotations:
      rule: https://example.com/rule/%d
      summary: Test case
    expr: up==0
    for: 1s
    labels:
      severity: severe
'''.lstrip().encode('utf-8')

TEST_SETTINGS = PromgenTest.data_yaml('examples', 'promgen.yml')


class RuleTest(PromgenTest):
    @mock.patch('django.dispatch.dispatcher.Signal.send')
    def setUp(self, mock_signal):
        self.user = self.add_force_login(id=999, username="Foo")
        self.site = models.Site.objects.get_current()
        self.shard = models.Shard.objects.create(name='Shard 1')
        self.service = models.Service.objects.create(id=999, name='Service 1')
        self.rule = models.Rule.objects.create(
            name='RuleName',
            clause='up==0',
            duration='1s',
            obj=self.site
        )
        models.RuleLabel.objects.create(name='severity', value='severe', rule=self.rule)
        models.RuleAnnotation.objects.create(name='summary', value='Test case', rule=self.rule)

    @override_settings(PROMGEN_SCHEME='https')
    @mock.patch('django.dispatch.dispatcher.Signal.send')
    def test_write_new(self, mock_post):
        result = prometheus.render_rules()
        self.assertEqual(result, _RULE_V2 % self.rule.id)

    @mock.patch('django.dispatch.dispatcher.Signal.send')
    def test_copy(self, mock_post):
        service = models.Service.objects.create(name='Service 2')
        copy = self.rule.copy_to(content_type='service', object_id=service.id)
        # Test that our copy has the same labels and annotations
        self.assertIn('severity', copy.labels)
        self.assertIn('summary', copy.annotations)
        # and test that we actually duplicated them and not moved them
        self.assertCount(models.RuleLabel, 3, 'Copied rule has exiting labels + service label')
        self.assertCount(models.RuleAnnotation, 2)

    @override_settings(PROMGEN=TEST_SETTINGS)
    @mock.patch("django.dispatch.dispatcher.Signal.send")
    def test_import_v2(self, mock_post):
        self.add_user_permissions("promgen.change_rule", "promgen.change_site")
        response = self.client.post(
            reverse("rule-import"),
            {"rules": PromgenTest.data("examples", "import.rule.yml")},
            follow=True,
        )

        # Includes count of our setUp rule + imported rules
        self.assertRoute(response, views.RuleImport, status=200)
        self.assertCount(models.Rule, 3, "Missing Rule")
        self.assertCount(models.RuleLabel, 4, "Missing labels")
        self.assertCount(models.RuleAnnotation, 9, "Missing annotations")

    @override_settings(PROMGEN=TEST_SETTINGS)
    @mock.patch("django.dispatch.dispatcher.Signal.send")
    def test_import_project_rule(self, mock_post):
        self.add_user_permissions("promgen.add_rule", "promgen.change_project")
        project = models.Project.objects.create(
            name="Project 1", service=self.service, shard=self.shard
        )
        response = self.client.post(
            reverse(
                "rule-new", kwargs={"content_type": "project", "object_id": project.id}
            ),
            {"rules": PromgenTest.data("examples", "import.rule.yml")},
            follow=True,
        )
        self.assertRoute(response, views.ProjectDetail, status=200)
        self.assertCount(models.Rule, 3, "Missing Rule")
        self.assertCount(models.RuleLabel, 4, "Missing labels")
        self.assertCount(models.RuleAnnotation, 9, "Missing annotations")

    @override_settings(PROMGEN=TEST_SETTINGS)
    @mock.patch("django.dispatch.dispatcher.Signal.send")
    def test_import_service_rule(self, mock_post):
        self.add_user_permissions("promgen.add_rule", "promgen.change_service")
        response = self.client.post(
            reverse(
                "rule-new",
                kwargs={"content_type": "service", "object_id": self.service.id},
            ),
            {"rules": PromgenTest.data("examples", "import.rule.yml")},
            follow=True,
        )
        self.assertRoute(response, views.ServiceDetail, status=200)
        self.assertCount(models.Rule, 3, "Missing Rule")
        self.assertCount(models.RuleLabel, 4, "Missing labels")
        self.assertCount(models.RuleAnnotation, 9, "Missing annotations")

    @mock.patch('django.dispatch.dispatcher.Signal.send')
    def test_missing_permission(self, mock_post):
        self.client.post(reverse('rule-import'), {
            'rules': PromgenTest.data('examples', 'import.rule.yml')
        })

        # Should only be a single rule from our initial setup
        self.assertCount(models.Rule, 1, 'Missing Rule')

    @mock.patch('django.dispatch.dispatcher.Signal.send')
    def test_macro(self, mock_post):
        self.project = models.Project.objects.create(name='Project 1', service=self.service, shard=self.shard)
        clause = 'up{%s}' % macro.EXCLUSION_MACRO

        rules = {
            'common': {'assert': 'up{service!~"Service 1"}'},
            'service': {'assert': 'up{service="Service 1",project!~"Project 1"}'},
            'project': {'assert': 'up{service="Service 1",project="Project 1",}'},
        }

        common_rule = models.Rule.objects.create(name='Common', clause=clause, duration='1s', obj=self.site)
        rules['common']['model'] = models.Rule.objects.get(pk=common_rule.pk)
        service_rule = common_rule.copy_to('service', self.service.id)
        rules['service']['model'] = models.Rule.objects.get(pk=service_rule.pk)
        project_rule = service_rule.copy_to('project', self.project.id)
        rules['project']['model'] = models.Rule.objects.get(pk=project_rule.pk)

        for k, r in rules.items():
            self.assertEquals(macro.rulemacro(r['model']), r['assert'], 'Expansion wrong for %s' % k)

    @override_settings(PROMGEN=TEST_SETTINGS)
    @mock.patch('django.dispatch.dispatcher.Signal.send')
    def test_invalid_annotation(self, mock_post):
        # $label.foo is invalid (should be $labels) so make sure we raise an exception
        models.RuleAnnotation.objects.create(name='summary', value='{{$label.foo}}', rule=self.rule)
        with self.assertRaises(ValidationError):
            prometheus.check_rules([self.rule])
