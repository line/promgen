# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

import promgen.templatetags.promgen as macro
from promgen import models, prometheus
from promgen.tests import TEST_RULE


_RULES = '''
ALERT RuleName
  IF up==0
  FOR 1s
  LABELS {severity="severe"}
  ANNOTATIONS {rule="http://example.com/rule/%d/edit", summary="Test case"}


'''.lstrip()


class RuleTest(TestCase):
    @mock.patch('django.db.models.signals.post_save', mock.Mock())
    @mock.patch('django.db.models.signals.pre_save', mock.Mock())
    def setUp(self):
        self.client.force_login(User.objects.create_user(id=999, username="Foo"), 'django.contrib.auth.backends.ModelBackend')
        self.shard = models.Shard.objects.create(name='Shard 1')
        self.service = models.Service.objects.create(id=1, name='Service 1', shard=self.shard)
        self.rule = models.Rule.create(
            name='RuleName',
            clause='up==0',
            duration='1s',
            obj=self.service
        )
        models.RuleLabel.objects.create(name='severity', value='severe', rule=self.rule)
        models.RuleAnnotation.objects.create(name='summary', value='Test case', rule=self.rule)

    @mock.patch('django.db.models.signals.post_save')
    def test_write(self, mock_render):
        result = prometheus.render_rules()
        self.assertEqual(result, _RULES % self.rule.id)

    @mock.patch('django.db.models.signals.post_save')
    def test_copy(self, mock_render):
        service = models.Service.objects.create(name='Service 2', shard=self.shard)
        copy = self.rule.copy_to(content_type='service', object_id=service.id)
        # Test that our copy has the same labels and annotations
        self.assertIn('severity', copy.labels)
        self.assertIn('summary', copy.annotations)
        # and test that we actually duplicated them and not moved them
        self.assertEqual(models.RuleLabel.objects.count(), 3, 'Copied rule has exiting labels + service label')
        self.assertEqual(models.RuleAnnotation.objects.count(), 2)

    @mock.patch('django.db.models.signals.post_save')
    def test_import(self, mock_render):
        self.client.post(reverse('import'), {
            'rules': TEST_RULE
        })

        # Includes count of our setUp rule + imported rules
        self.assertEqual(models.Rule.objects.count(), 3, 'Missing Rule')
        self.assertEqual(models.RuleLabel.objects.count(), 4, 'Missing labels')
        self.assertEqual(models.RuleAnnotation.objects.count(), 7, 'Missing annotations')

    @mock.patch('django.db.models.signals.post_save')
    def test_macro(self, mock_signals):
        self.project = models.Project.objects.create(name='Project 1', service=self.service)
        clause = 'up{%s}' % macro.EXCLUSION_MACRO

        rules = {
            'common': {'assert': 'up{service!~"Service 1"}'},
            'service': {'assert': 'up{service="Service 1",project!~"Project 1"}'},
            'project': {'assert': 'up{service="Service 1",project="Project 1",}'},
        }

        common_rule = models.Rule.create(name='Common', clause=clause, duration='1s', obj=self.service.default())
        rules['common']['model'] = models.Rule.objects.get(pk=common_rule.pk)
        service_rule = common_rule.copy_to('service', self.service.id)
        rules['service']['model'] = models.Rule.objects.get(pk=service_rule.pk)
        project_rule = service_rule.copy_to('project', self.project.id)
        rules['project']['model'] = models.Rule.objects.get(pk=project_rule.pk)

        for k, r in rules.items():
            self.assertEquals(macro.rulemacro(r['model'].clause, r['model']), r['assert'], 'Expansion wrong for %s' % k)
