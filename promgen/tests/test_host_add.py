# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE


from django.urls import reverse

from promgen import forms, models
from promgen.tests import PromgenTest


class HostTests(PromgenTest):
    longMessage = True
    fixtures = ["testcases.yaml"]

    def setUp(self):
        self.add_force_login(id=999, username="Foo")

    def test_newline(self):
        self.client.post(
            reverse("hosts-add", args=[1]),
            {"hosts": "\naaa.example.com\nbbb.example.com\nccc.example.com \n"},
            follow=False,
        )
        self.assertCount(models.Host, 3, "Expected 3 hosts")

    def test_comma(self):
        self.client.post(
            reverse("hosts-add", args=[1]),
            {"hosts": ",,aaa.example.com, bbb.example.com,ccc.example.com,"},
            follow=False,
        )
        self.assertCount(models.Host, 3, "Expected 3 hosts")

    def test_invalid(self):
        form = forms.HostForm(
            {
                "hosts": """
            foo/bar/baz
            not-a-valid:host
            """
            }
        )
        self.assertFalse(form.is_valid(), "Form uses invalid hosts")
        self.assertEquals(form.errors, {"__all__": ["Invalid hostname foo/bar/baz"]})
