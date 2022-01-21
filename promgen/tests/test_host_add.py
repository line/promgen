# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE


from django.urls import reverse

from promgen import forms, models
from promgen.tests import PromgenTest


class RouteTests(PromgenTest):
    longMessage = True

    def setUp(self):
        self.add_force_login(id=999, username="Foo")

    def test_newline(self):
        farm = models.Farm.objects.create(name='Foo')
        self.client.post(reverse('hosts-add', args=[farm.pk]), {
            'hosts': "\naaa\nbbb\nccc \n"
        }, follow=False)
        self.assertCount(models.Host, 3, "Expected 3 hosts")

    def test_comma(self):
        farm = models.Farm.objects.create(name='Foo')
        self.client.post(reverse('hosts-add', args=[farm.pk]), {
            'hosts': ",,aaa, bbb,ccc,"
        }, follow=False)
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
