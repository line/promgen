# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

from unittest import mock

import factory.django
from django.contrib.auth.models import User, Permission
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
        self.user = User.objects.create_user(id=999, username="Foo")
        self.client.force_login(self.user, 'django.contrib.auth.backends.ModelBackend')

    @override_settings(PROMGEN=TEST_SETTINGS)
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_alert(self):
        response = self.client.post(reverse('alert'), data=TEST_ALERT, content_type='application/json')
        self.assertEqual(response.status_code, 202)

    @override_settings(PROMGEN=TEST_SETTINGS)
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @mock.patch('promgen.signals._trigger_write_config')
    @mock.patch('promgen.prometheus.reload_prometheus')
    def test_import(self, mock_write, mock_reload):
        self.user.user_permissions.add(
            Permission.objects.get(codename='change_rule'),
            Permission.objects.get(codename='change_site'),
            Permission.objects.get(codename='change_exporter'),
        )
        response = self.client.post(reverse('import'), {'config': TEST_IMPORT})

        self.assertEqual(response.status_code, 302, 'Redirect to imported object')
        self.assertEqual(models.Service.objects.count(), 1, 'Import one service')
        self.assertEqual(models.Project.objects.count(), 2, 'Import two projects')
        self.assertEqual(models.Exporter.objects.count(), 2, 'Import two exporters')
        self.assertEqual(models.Host.objects.count(), 3, 'Import three hosts')
        self.assertEqual(models.Farm.objects.filter(source='pmc').count(), 1, 'One PMC Farm')
        self.assertEqual(models.Farm.objects.filter(source='other').count(), 1, 'One other Farm')

    @override_settings(PROMGEN=TEST_SETTINGS)
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @mock.patch('promgen.signals._trigger_write_config')
    @mock.patch('promgen.prometheus.reload_prometheus')
    def test_replace(self, mock_write, mock_reload):
        # Set the required permissions
        self.user.user_permissions.add(
            Permission.objects.get(codename='change_rule'),
            Permission.objects.get(codename='change_site'),
            Permission.objects.get(codename='change_exporter'),
        )

        response = self.client.post(reverse('import'), {'config': TEST_IMPORT})
        self.assertEqual(response.status_code, 302, 'Redirect to imported object')

        response = self.client.post(reverse('import'), {'config': TEST_REPLACE})
        self.assertEqual(response.status_code, 302, 'Redirect to imported object (2)')

        self.assertEqual(models.Service.objects.count(), 1, 'Import one service')
        self.assertEqual(models.Project.objects.count(), 2, 'Import two projects')
        self.assertEqual(models.Exporter.objects.count(), 2, 'Import two exporters')
        self.assertEqual(models.Farm.objects.count(), 3, 'Original two farms and one new farm')
        self.assertEqual(models.Host.objects.count(), 5, 'Original 3 hosts and two new ones')

    def test_service(self):
        response = self.client.get(reverse('service-list'))
        self.assertEqual(response.status_code, 200)

    def test_project(self):
        shard = models.Shard.objects.create(name='Shard Test')
        service = models.Service.objects.create(name='Service Test', shard=shard)
        project = models.Project.objects.create(name='Project Test', service=service)

        response = self.client.get(reverse('project-detail', kwargs={'pk': project.pk}))
        self.assertEqual(response.status_code, 200)

    def test_farms(self):
        response = self.client.get(reverse('farm-list'))
        self.assertEqual(response.status_code, 200)

    def test_hosts(self):
        response = self.client.get(reverse('host-list'))
        self.assertEqual(response.status_code, 200)

    @mock.patch('promgen.util.get')
    def test_scrape(self, mock_get):
        project = self.factory(models.Project, 'test_scrape')
        project.farm = models.Farm.objects.create(name='test_scrape')
        project.farm.host_set.create(name='example.com')
        project.save()

        # Uses the scrape target as the key, and the POST body that should
        # result in that URL
        exporters = {
            'http://example.com:8000/metrics': {
                'target': '#exporterresult',
                'job': 'foo',
                'port': 8000
            },
            'http://example.com:8000/foo': {
                'target': '#exporterresult',
                'job': 'foo',
                'port': 8000,
                'path': '/foo'
            }
        }

        for url, body in exporters.items():
            # For each POST body, check to see that we generate and attempt to
            # scrape the correct URL
            self.client.post(
                reverse('exporter-scrape', args=(project.pk, )),
                body,
            )
            self.assertEqual(mock_get.call_args[0][0], url)

    def test_failed_permission(self):
        # Test for redirect
        for request in [{'viewname': 'rule-new', 'args': ('site', 1)}]:
            response = self.client.get(reverse(**request))
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.url.startswith('/login'))

    def test_other_routes(self):
        self.user.user_permissions.add(
            Permission.objects.get(codename='add_rule'),
            Permission.objects.get(codename='change_site'),
        )
        for request in [{'viewname': 'rule-new', 'args': ('site', 1)}]:
            response = self.client.get(reverse(**request))
            self.assertEqual(response.status_code, 200)
