# Copyright (c) 2020 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE
from unittest import mock

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError

from promgen import models, validators
from promgen.shortcuts import resolve_domain
from promgen.tests import PromgenTest


class ModelTest(PromgenTest):
    def setUp(self):
        self.user = self.force_login(username="demo")

    def test_names(self):
        # Unicode is ok
        models.Service(name=r"日本語", owner=self.user).full_clean()
        # Spaces are ok
        models.Service(name=r"foo bar", owner=self.user).full_clean()
        # dash or under score are ok
        models.Service(name=r"foo-bar_baz", owner=self.user).full_clean()
        with self.assertRaises(ValidationError):
            # Fail a name with \
            models.Service(name=r"foo/bar", owner=self.user).full_clean()
            models.Service(name=r"foo\bar", owner=self.user).full_clean()

    def test_validators(self):
        with self.assertRaises(ValidationError, msg="Javascript injection"):
            validators.metricname(
                "asdasd[[1-1]]')) || (this.$el.ownerDocument.defaultView.alert('1337",
            )

        with self.assertRaises(ValidationError, msg="Vue.js injection"):
            validators.metricname(
                "[[this.$el.ownerDocument.defaultView.alert(1337)]]",
            )

    @mock.patch("django.dispatch.dispatcher.Signal.send")
    def test_rule_annotation(self, mock_post):
        # Check if annotation["rule"] is automatically set to be {domain}/rule/{id} when creating a
        # new rule
        rule = models.Rule(
            name="example-rule",
            content_type=ContentType.objects.get_for_model(models.Site),
            object_id=1,
            clause="up==1",
            duration="1s",
        )
        rule.save()
        self.assertEqual(resolve_domain("rule-detail", rule.pk), rule.annotations["rule"])

        # Check if annotation["rule"] is automatically set to be {domain}/rule/{id} when updating an
        # existed rule
        rule.name = "another-example-rule"
        rule.annotations["rule"] = "another-annotation-value"
        rule.save()
        self.assertEqual(resolve_domain("rule-detail", rule.pk), rule.annotations["rule"])

        # Check if annotation["rule"] is still set to be {domain}/rule/{id} when trying to remove
        # annotation["rule"]
        rule.annotations["rule"] = None
        rule.save()
        self.assertEqual(resolve_domain("rule-detail", rule.pk), rule.annotations["rule"])

        # Check if annotation["rule"] of new rule is automatically set to be {domain}/rule/{id}
        # when cloning an existed rule
        new_rule = rule.copy_to(content_type="service", object_id=2)
        self.assertEqual(resolve_domain("rule-detail", rule.pk), rule.annotations["rule"])
        self.assertEqual(resolve_domain("rule-detail", new_rule.pk), new_rule.annotations["rule"])
