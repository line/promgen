# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

from unittest import mock

from django.contrib.auth.models import User, Permission
from django.urls import reverse

import promgen.templatetags.promgen as macro
from django.core.exceptions import ValidationError
from promgen import models, prometheus
from promgen.tests import PromgenTest

_RULES = '''
ALERT RuleName
  IF up==0
  FOR 1s
  LABELS {severity="severe"}
  ANNOTATIONS {rule="http://example.com/rule/%d/edit", summary="Test case"}


'''.lstrip().encode('utf-8')

_RULE_NEW = '''
groups:
- name: example.com
  rules:
  - alert: RuleName
    annotations:
      rule: http://example.com/rule/%d/edit
      summary: Test case
    expr: up==0
    for: 1s
    labels:
      severity: severe
'''.lstrip().encode('utf-8')


class RuleTest(PromgenTest):
    @mock.patch('django.dispatch.dispatcher.Signal.send')
    def setUp(self, mock_signal):
        self.user = User.objects.create_user(id=999, username="Foo")
        self.client.force_login(self.user)
        self.shard = models.Shard.objects.create(name='Shard 1')
        self.site = models.Site.objects.get_current()
        self.service = models.Service.objects.create(id=999, name='Service 1', shard=self.shard)
        self.rule = models.Rule.objects.create(
            name='RuleName',
            clause='up==0',
            duration='1s',
            obj=self.site
        )
        models.RuleLabel.objects.create(name='severity', value='severe', rule=self.rule)
        models.RuleAnnotation.objects.create(name='summary', value='Test case', rule=self.rule)

    @mock.patch('django.dispatch.dispatcher.Signal.send')
    def test_write_old(self, mock_post):
        result = prometheus.render_rules(version=1)
        self.assertEqual(result, _RULES % self.rule.id)

    @mock.patch('django.dispatch.dispatcher.Signal.send')
    def test_write_new(self, mock_post):
        result = prometheus.render_rules(version=2)
        self.assertEqual(result, _RULE_NEW % self.rule.id)

    @mock.patch('django.dispatch.dispatcher.Signal.send')
    def test_copy(self, mock_post):
        service = models.Service.objects.create(name='Service 2', shard=self.shard)
        copy = self.rule.copy_to(content_type='service', object_id=service.id)
        # Test that our copy has the same labels and annotations
        self.assertIn('severity', copy.labels)
        self.assertIn('summary', copy.annotations)
        # and test that we actually duplicated them and not moved them
        self.assertEqual(models.RuleLabel.objects.count(), 3, 'Copied rule has exiting labels + service label')
        self.assertEqual(models.RuleAnnotation.objects.count(), 2)

    @mock.patch('django.dispatch.dispatcher.Signal.send')
    def test_import_v1(self, mock_post):
        self.user.user_permissions.add(
            Permission.objects.get(codename='change_rule'),
            Permission.objects.get(codename='change_site'),
        )
        self.client.post(reverse('rule-import'), {
            'rules': PromgenTest.data('examples', 'import.rule')
        })

        # Includes count of our setUp rule + imported rules
        self.assertEqual(models.Rule.objects.count(), 3, 'Missing Rule')
        self.assertEqual(models.RuleLabel.objects.count(), 4, 'Missing labels')
        self.assertEqual(models.RuleAnnotation.objects.count(), 7, 'Missing annotations')

    @mock.patch('django.dispatch.dispatcher.Signal.send')
    def test_import_v2(self, mock_post):
        self.user.user_permissions.add(
            Permission.objects.get(codename='change_rule'),
            Permission.objects.get(codename='change_site'),
        )
        self.client.post(reverse('rule-import'), {
            'rules': PromgenTest.data('examples', 'import.rule.yml')
        })

        # Includes count of our setUp rule + imported rules
        self.assertEqual(models.Rule.objects.count(), 3, 'Missing Rule')
        self.assertEqual(models.RuleLabel.objects.count(), 4, 'Missing labels')
        self.assertEqual(models.RuleAnnotation.objects.count(), 9, 'Missing annotations')

    @mock.patch('django.dispatch.dispatcher.Signal.send')
    def test_missing_permission(self, mock_post):
        self.client.post(reverse('rule-import'), {
            'rules': PromgenTest.data('examples', 'import.rule.yml')
        })

        # Should only be a single rule from our initial setup
        self.assertEqual(models.Rule.objects.count(), 1, 'Missing Rule')

    @mock.patch('django.dispatch.dispatcher.Signal.send')
    def test_macro(self, mock_post):
        self.project = models.Project.objects.create(name='Project 1', service=self.service)
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
            self.assertEquals(macro.rulemacro(r['model'].clause, r['model']), r['assert'], 'Expansion wrong for %s' % k)

    @mock.patch('django.dispatch.dispatcher.Signal.send')
    def test_invalid_annotation(self, mock_post):
        # $label.foo is invalid (should be $labels) so make sure we raise an exception
        models.RuleAnnotation.objects.create(name='summary', value='{{$label.foo}}', rule=self.rule)
        with self.assertRaises(ValidationError):
            prometheus.check_rules([self.rule])
