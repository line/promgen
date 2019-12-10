# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE


from promgen import models
from promgen.tests import PromgenTest

from django.urls import reverse


class RouteTests(PromgenTest):
    longMessage = True

    def setUp(self):
        self.add_force_login(id=999, username="Foo")

    def test_newline(self):
        farm = models.Farm.objects.create(name="Foo")
        self.client.post(
            reverse("hosts-add", args=[farm.pk]),
            {"hosts": "\naaa\nbbb\nccc \n"},
            follow=False,
        )
        self.assertCount(models.Host, 3, "Expected 3 hosts")

    def test_comma(self):
        farm = models.Farm.objects.create(name="Foo")
        self.client.post(
            reverse("hosts-add", args=[farm.pk]),
            {"hosts": ",,aaa, bbb,ccc,"},
            follow=False,
        )
        self.assertCount(models.Host, 3, "Expected 3 hosts")
