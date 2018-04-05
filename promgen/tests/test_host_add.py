# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

from unittest import mock

import factory.django
from django.contrib.auth.models import User
from django.db.models.signals import post_save, pre_save
from django.test import override_settings
from django.urls import reverse

from promgen import models
from promgen.tests import PromgenTest

TEST_SETTINGS = PromgenTest.data_yaml('examples', 'promgen.yml')
TEST_ALERT = PromgenTest.data('examples', 'alertmanager.json')
TEST_IMPORT = PromgenTest.data('examples', 'import.json')
TEST_REPLACE = PromgenTest.data('examples', 'replace.json')


class RouteTests(PromgenTest):
    longMessage = True

    @factory.django.mute_signals(pre_save, post_save)
    def setUp(self):
        self.client.force_login(User.objects.create_user(id=999, username="Foo"), 'django.contrib.auth.backends.ModelBackend')

    def test_newline(self):
        farm = models.Farm.objects.create(name='Foo')
        self.client.post(reverse('hosts-add', args=[farm.pk]), {
            'hosts': "\naaa\nbbb\nccc \n"
        }, follow=False)
        self.assertEqual(models.Host.objects.count(), 3, 'Expected 3 hosts')

    def test_comma(self):
        farm = models.Farm.objects.create(name='Foo')
        self.client.post(reverse('hosts-add', args=[farm.pk]), {
            'hosts': ",,aaa, bbb,ccc,"
        }, follow=False)
        self.assertEqual(models.Host.objects.count(), 3, 'Expected 3 hosts')
