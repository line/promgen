from unittest import mock

from promgen.tests import PromgenTest
from promgen import models
from promgen import prometheus
from promgen import tests

TEST_CONFIG = tests.Data('examples', 'prometheus.config.json').json()


class PrometheusConfigTest(PromgenTest):
    fixtures = ['testcases.yaml', 'testcases-prometheus.yaml']

    @mock.patch('django.dispatch.dispatcher.Signal.send')
    def setUp(self, mock_signal):
        self.force_login(username='demo')

    def test_create_config(self):
        expected_config = TEST_CONFIG['create_config']

        actual_config = prometheus.create_config()

        self.assertEqual(expected_config, actual_config)

    def test_create_config_for_service_and_project(self):
        expected_config = TEST_CONFIG['create_config_for_service_and_project']
        service = models.Service.objects.get(name='test-service')
        project = models.Project.objects.get(name='another-project')

        actual_config = prometheus.create_config(service, project)

        self.assertEqual(expected_config, actual_config)
