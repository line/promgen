# Copyright (c) 2018 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE


from django.test import override_settings
from django.urls import reverse
from unittest import mock
import requests

from promgen import models, rest, tests


class RestAPITest(tests.PromgenTest):
    @override_settings(PROMGEN=tests.SETTINGS)
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_alert_blackhole(self):
        response = self.fireAlert("heartbeat.json")
        self.assertRoute(response, rest.AlertReceiver, 202)
        self.assertCount(models.Alert, 0, "Heartbeat alert should be deleted")

    @override_settings(PROMGEN=tests.SETTINGS)
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_alert(self):
        response = self.fireAlert()
        self.assertEqual(response.status_code, 202)
        self.assertCount(models.Alert, 1, "Alert Queued")


class ProjectRestAPITest(tests.PromgenTest):
    fixtures = ['testcases.yaml', 'testcases-prometheus.yaml']

    def setUp(self):
        self.force_login(username='admin')
        project = models.Project.objects.get(pk=1)
        self.url = reverse('api:project-scrape', kwargs={'name': project.name})

    @staticmethod
    def __mock_get_side_effect(scrape_url, params=None, **kwargs):
        scrape_response = requests.Response()
        scrape_response.url = scrape_url
        scrape_response.status_code = 200
        return scrape_response

    @mock.patch("requests.get")
    def test_should_return_200_when_valid_exporter_id_is_passed(self, mock_get):
        mock_get.side_effect = self.__mock_get_side_effect

        response = self.client.post(self.url, {'exporter_id': 1}, content_type='application/json')

        self.assertEqual(200, response.status_code)
        self.assertEqual({
            'http://host1:1111/path1?target=prometheus.io': 200,
            'http://host2:1111/path1?target=prometheus.io': 200,
        }, response.json())

    @mock.patch("requests.get")
    def test_should_return_400_when_invalid_exporter_id_is_passed(self, mock_get):
        mock_get.side_effect = self.__mock_get_side_effect

        response = self.client.post(self.url, {'exporter_id': -1}, content_type='application/json')

        self.assertEqual(400, response.status_code)
        self.assertEqual({
            'error': {'exporter_id': ["Exporter with id '-1' is not found"]},
        }, response.json())

    @mock.patch("requests.get")
    def test_should_return_400_when_incorrect_data_is_passed(self, mock_get):
        mock_get.side_effect = self.__mock_get_side_effect

        response = self.client.post(self.url, {'scheme': 'http'}, content_type='application/json')

        self.assertEqual(400, response.status_code)
        self.assertEqual({
            'error': {'non_field_errors': ['Either exporter_id either scheme, port, path are required']},
        }, response.json())

    @mock.patch("requests.get")
    def test_should_return_200_when_correct_data_is_passed(self, mock_get):
        mock_get.side_effect = self.__mock_get_side_effect

        data = {'scheme': 'http', 'port': 9115, 'path': '', 'query': {'foo': 'bar', 'target': 'prometheus.io'}}
        response = self.client.post(self.url, data, content_type='application/json')

        # self.assertEqual(200, response.status_code)
        self.assertEqual({
            'http://host1:9115/metrics?foo=bar&target=prometheus.io': 200,
            'http://host2:9115/metrics?foo=bar&target=prometheus.io': 200,
        }, response.json())

    def test_should_return_400_when_port_is_incorrect(self):
        data = {'scheme': 'http', 'port': 0, 'path': '/metrics', 'query': {'foo': 'bar', 'target': 'prometheus.io'}}
        response = self.client.post(self.url, data, content_type='application/json')

        self.assertEqual(400, response.status_code)
        self.assertEqual({
            'error': {'port': ['Port should be greater than 0 and lower than 65536']}
        }, response.json())

    def test_should_return_400_when_scheme_is_incorrect(self):
        data = {'scheme': 'ftp', 'port': 25, 'path': '/metrics', 'query': {'foo': 'bar', 'target': 'prometheus.io'}}
        response = self.client.post(self.url, data, content_type='application/json')

        self.assertEqual(400, response.status_code)
        self.assertEqual({
            'error': {'scheme': ['Scheme should be http or https']}
        }, response.json())
