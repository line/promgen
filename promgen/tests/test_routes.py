import json
from unittest import mock

from django.test import TestCase, override_settings
from django.urls import reverse

from promgen import models
from promgen.tests import TEST_ALERT, TEST_IMPORT, TEST_SETTINGS


class RouteTests(TestCase):
    longMessage = True

    @override_settings(PROMGEN=TEST_SETTINGS)
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_alert(self):
        response = self.client.post(reverse('alert'), data=json.dumps(TEST_ALERT), content_type='application/json')
        self.assertEqual(response.status_code, 200)

    @override_settings(PROMGEN=TEST_SETTINGS)
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @mock.patch('promgen.signals._trigger_write_config')
    @mock.patch('promgen.prometheus.reload_prometheus')
    @mock.patch('promgen.prometheus.notify')
    def test_import(self, mock_write, mock_reload, mock_notify):
        response = self.client.post(reverse('import'), {
            'config': json.dumps(TEST_IMPORT)
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(models.Service.objects.count(), 1, 'Import one service')
        self.assertEqual(models.Project.objects.count(), 2, 'Import two projects')
        self.assertEqual(models.Exporter.objects.count(), 2, 'Import two exporters')
        self.assertEqual(models.Host.objects.count(), 3, 'Import three hosts')
        self.assertEqual(models.Farm.objects.filter(source='pmc').count(), 1, 'One PMC Farm')
        self.assertEqual(models.Farm.objects.filter(source='other').count(), 1, 'One other Farm')

    def test_service(self):
        response = self.client.get(reverse('service-list'))
        self.assertEqual(response.status_code, 200)

    def test_project(self):
        service = models.Service.objects.create(name='Service Test')
        project = models.Project.objects.create(name='Project Test', service=service)

        response = self.client.get(reverse('project-detail', kwargs={'pk': project.pk}))
        self.assertEqual(response.status_code, 200)

    def test_farms(self):
        response = self.client.get(reverse('farm-list'))
        self.assertEqual(response.status_code, 200)

    def test_hosts(self):
        response = self.client.get(reverse('host-list'))
        self.assertEqual(response.status_code, 200)
