import json
from unittest import mock

from django.test import TestCase, override_settings
from django.urls import reverse

from promgen import models
from promgen.tests import TEST_ALERT, TEST_IMPORT, TEST_SETTINGS


class RouteTests(TestCase):
    longMessage = True

    @override_settings(PROMGEN=TEST_SETTINGS)
    def test_alert(self):
        response = self.client.post(reverse('alert'), data=json.dumps(TEST_ALERT), content_type='application/json')
        self.assertEqual(response.status_code, 200)

    @mock.patch('promgen.signals._write_config')
    def test_import(self, mock_reload):
        response = self.client.post(reverse('import'), {
            'config': json.dumps(TEST_IMPORT)
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(models.Service.objects.count(), 1, 'Import one service')
        self.assertEqual(models.Project.objects.count(), 2, 'Import two projects')
        self.assertEqual(models.Exporter.objects.count(), 2, 'Import two exporters')
        self.assertEqual(models.Host.objects.count(), 3, 'Import three hosts')
