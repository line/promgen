# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE
from django.shortcuts import get_object_or_404
from django.urls import reverse
from guardian.shortcuts import assign_perm

from promgen import models, validators
from promgen.middleware import get_current_user
from promgen.tests import PromgenTest


class HostTests(PromgenTest):
    def setUp(self):
        self.force_login(username="demo")

    # For our first two tests, we just want to make sure that both newline
    # separated and comma separated work, but are not necessarily testing
    # valid/invalid hostnames
    def test_newline(self):
        assign_perm("promgen.farm_editor", get_current_user(), get_object_or_404(models.Farm, pk=1))
        self.client.post(
            reverse("hosts-add", args=[1]),
            {"hosts": "\naaa.example.com\nbbb.example.com\nccc.example.com \n"},
            follow=False,
        )
        self.assertCount(models.Host, 3, "Expected 3 hosts")

    def test_comma(self):
        assign_perm("promgen.farm_editor", get_current_user(), get_object_or_404(models.Farm, pk=1))
        self.client.post(
            reverse("hosts-add", args=[1]),
            {"hosts": ",,aaa.example.com, bbb.example.com,ccc.example.com,"},
            follow=False,
        )
        self.assertCount(models.Host, 3, "Expected 3 hosts")

    # Within our new host code, the hosts are split (by newline or comma) and then
    # individually tested. Here we will test our validator on specific entries that
    # should pass or fail
    def test_validators(self):
        # Hostname only should be valid
        validators.hostname("bare-hostname")
        # FQDN should be valid
        validators.hostname("fqdn.example.com")
        # UPPERCASE and trailing dot should also be fine
        validators.hostname("FQDN.with.trailing.dot.example.com.")
        # Hostname cannot contain underscore
        with self.assertRaises(validators.ValidationError):
            validators.hostname("underscore_in_hostname")
        # Hostname should not include port
        with self.assertRaises(validators.ValidationError):
            validators.hostname("invalid:host")
        # Hostname should not be a url (no scheme)
        with self.assertRaises(validators.ValidationError):
            validators.hostname("http://example.com")
        # Hostnames should not contain a path component
        with self.assertRaises(validators.ValidationError):
            validators.hostname("example.com/path")
