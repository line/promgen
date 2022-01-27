from unittest import mock

from promgen.tests import PromgenTest
from promgen import models
from promgen import prometheus


class PrometheusConfigTest(PromgenTest):
    fixtures = ['testcases.yaml', 'testcases-prometheus.yaml']

    @mock.patch('django.dispatch.dispatcher.Signal.send')
    def setUp(self, mock_signal):
        self.force_login(username='demo')

    def test_create_config(self):
        config = prometheus.create_config()
        self.assertEqual(config, [
            {
                'labels': {
                    '__shard': 'test-shard',
                    'service': 'test-service',
                    'project': 'test-project',
                    'farm': 'test-farm',
                    '__farm_source': '',
                    'job': 'exporter1',
                    '__scheme__': 'http',
                    '__metrics_path__': '/path1',
                    '__param_target': 'prometheus.io',
                    'target': 'prometheus.io',
                },
                'targets': ['host1:1111', 'host2:1111'],
            },
            {
                'labels': {
                    '__shard': 'test-shard',
                    'service': 'test-service',
                    'project': 'test-project',
                    'farm': 'test-farm',
                    '__farm_source': '',
                    'job': 'exporter2',
                    '__scheme__': 'https',
                    '__metrics_path__': '/path2',
                    'name2_1': 'value2_1',
                    'name2_2': 'value2_2',
                },
                'targets': ['host1:2222', 'host2:2222'],
            },
            {
                'labels': {
                    '__shard': 'test-shard',
                    'service': 'test-service',
                    'project': 'another-project',
                    'farm': 'test-farm',
                    '__farm_source': '',
                    'job': 'exporter4',
                    '__scheme__': 'http',
                    '__metrics_path__': '/path4',
                    'name4_1': 'value4_1',
                    'name4_2': 'value4_2',
                },
                'targets': ['host1:4444', 'host2:4444'],
            },
            {
                'labels': {
                    '__shard': 'test-shard',
                    'service': 'test-service',
                    'project': 'another-project',
                    'farm': 'test-farm',
                    '__farm_source': '',
                    'job': 'exporter5',
                    '__scheme__': 'https',
                    'name5_1': 'value5_1',
                    'name5_2': 'value5_2',
                },
                'targets': ['host1:5555', 'host2:5555'],
            },
            {
                'labels': {
                    '__shard': 'test-shard',
                    'service': 'other-service',
                    'project': 'yet-another-project',
                    'farm': 'test-farm',
                    '__farm_source': '',
                    'job': 'exporter7',
                    '__scheme__': 'http',
                    '__metrics_path__': '/path7',
                    'name7_1': 'value7_1',
                    'name7_2': 'value7_2',
                },
                'targets': ['host1:7777', 'host2:7777'],
            },
            {
                'labels': {
                    '__shard': 'test-shard',
                    'service': 'other-service',
                    'project': 'yet-another-project',
                    'farm': 'test-farm',
                    '__farm_source': '',
                    'job': 'exporter8',
                    '__scheme__': 'https',
                    '__metrics_path__': '/path8',
                },
                'targets': ['host1:8888', 'host2:8888'],
            },
        ])

    def test_create_config_for_service_and_project(self):
        service = models.Service.objects.get(name='test-service')
        project = models.Project.objects.get(name='another-project')
        config = prometheus.create_config(service, project)
        self.assertEqual(config, [
            {
                'labels': {
                    '__shard': 'test-shard',
                    'service': 'test-service',
                    'project': 'another-project',
                    'farm': 'test-farm',
                    '__farm_source': '',
                    'job': 'exporter4',
                    '__scheme__': 'http',
                    '__metrics_path__': '/path4',
                    'name4_1': 'value4_1',
                    'name4_2': 'value4_2',
                },
                'targets': ['host1:4444', 'host2:4444'],
            },
            {
                'labels': {
                    '__shard': 'test-shard',
                    'service': 'test-service',
                    'project': 'another-project',
                    'farm': 'test-farm',
                    '__farm_source': '',
                    'job': 'exporter5',
                    '__scheme__': 'https',
                    'name5_1': 'value5_1',
                    'name5_2': 'value5_2',
                },
                'targets': ['host1:5555', 'host2:5555'],
            },
        ])
