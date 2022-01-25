from unittest import mock

from promgen.tests import PromgenTest
from promgen import models
from promgen import prometheus


class PrometheusConfigTest(PromgenTest):
    @mock.patch('django.dispatch.dispatcher.Signal.send')
    def setUp(self, mock_signal):
        user_id = 999
        user = self.add_force_login(id=user_id, username='Tester')
        self.__create_services([
            {
                'name': 'service1',
                'owner': user,
                'projects': [
                    {
                        'name': 'project1',
                        'owner': user,
                        'farm': {'name': 'farm1', 'hosts': ['host1', 'host2']},
                        'shard': {'name': 'shard1'},
                        'exporters': [
                            {
                                'job': 'exporter1',
                                'port': 1111,
                                'path': '/path1',
                                'scheme': 'http',
                                'enabled': True,
                                'labels': [('target', 'prometheus.io', True), ('name1_2', 'value1_2'),
                                           ('__farm_source', 'should be skipped')],
                            },
                            {
                                'job': 'exporter2',
                                'port': 2222,
                                'path': '/path2',
                                'scheme': 'https',
                                'enabled': True,
                                'labels': [('name2_1', 'value2_1'), ('name2_2', 'value2_2')],
                            },
                            {
                                'job': 'disabled exporter',
                                'port': 0000,
                                'path': '/path0',
                                'scheme': 'https',
                                'enabled': False,
                                'labels': [('name0_1', 'value0_1'), ('name0_2', 'value0_2')],
                            },
                        ],
                    },
                    {
                        'name': 'project2',
                        'owner': user,
                        'farm': {'name': 'farm2', 'hosts': ['host1', 'host2']},
                        'shard': {'name': 'shard2'},
                        'exporters': [
                            {
                                'job': 'exporter3',
                                'port': 3333,
                                'path': '/path3',
                                'scheme': 'http',
                                'enabled': True,
                                'labels': [('name3_1', 'value3_1'), ('name3_2', 'value3_2')],
                            },
                            {
                                'job': 'exporter4',
                                'port': 4444,
                                'path': '',
                                'scheme': 'https',
                                'enabled': True,
                                'labels': [('name4_1', 'value4_1'), ('name4_2', 'value4_2')],
                            },
                        ],
                    },
                    {
                        'name': 'project without farm',
                        'owner': user,
                        'shard': {'name': 'shard0'},
                        'exporters': [
                            {
                                'job': 'exporter0',
                                'port': 0000,
                                'path': '/path0',
                                'scheme': 'http',
                                'enabled': True,
                                'labels': [('name1', 'value1'), ('name2', 'value2')],
                            },
                        ],
                    },
                ],
            },
            {
                'name': 'service2',
                'owner': user,
                'projects': [
                    {
                        'name': 'project3',
                        'owner': user,
                        'farm': {'name': 'farm3', 'hosts': ['host1', 'host2']},
                        'shard': {'name': 'shard3'},
                        'exporters': [
                            {
                                'job': 'exporter5',
                                'port': 5555,
                                'path': '/path5',
                                'scheme': 'http',
                                'enabled': True,
                                'labels': [('name5_1', 'value5_1'), ('name5_2', 'value5_2')],
                            },
                            {
                                'job': 'exporter6',
                                'port': 6666,
                                'path': '/path6',
                                'scheme': 'https',
                                'enabled': True,
                                'labels': [],
                            },
                        ],
                    },
                ],
            },
        ])

    def test_create_config(self):
        config = prometheus.create_config()
        self.assertEqual(config, [
            {
                'labels': {
                    '__shard': 'shard1',
                    'service': 'service1',
                    'project': 'project1',
                    'farm': 'farm1',
                    '__farm_source': '',
                    'job': 'exporter1',
                    '__scheme__': 'http',
                    '__metrics_path__': '/path1',
                    '__param_target': 'prometheus.io',
                    'name1_2': 'value1_2',
                },
                'targets': ['host1:1111', 'host2:1111'],
            },
            {
                'labels': {
                    '__shard': 'shard1',
                    'service': 'service1',
                    'project': 'project1',
                    'farm': 'farm1',
                    '__farm_source': '',
                    'job': 'exporter2',
                    '__scheme__': 'http',
                    '__metrics_path__': '/path2',
                    'name2_1': 'value2_1',
                    'name2_2': 'value2_2',
                },
                'targets': ['host1:2222', 'host2:2222'],
            },
            {
                'labels': {
                    '__shard': 'shard2',
                    'service': 'service1',
                    'project': 'project2',
                    'farm': 'farm2',
                    '__farm_source': '',
                    'job': 'exporter3',
                    '__scheme__': 'http',
                    '__metrics_path__': '/path3',
                    'name3_1': 'value3_1',
                    'name3_2': 'value3_2',
                },
                'targets': ['host1:3333', 'host2:3333'],
            },
            {
                'labels': {
                    '__shard': 'shard2',
                    'service': 'service1',
                    'project': 'project2',
                    'farm': 'farm2',
                    '__farm_source': '',
                    'job': 'exporter4',
                    '__scheme__': 'http',
                    'name4_1': 'value4_1',
                    'name4_2': 'value4_2',
                },
                'targets': ['host1:4444', 'host2:4444'],
            },
            {
                'labels': {
                    '__shard': 'shard3',
                    'service': 'service2',
                    'project': 'project3',
                    'farm': 'farm3',
                    '__farm_source': '',
                    'job': 'exporter5',
                    '__scheme__': 'http',
                    '__metrics_path__': '/path5',
                    'name5_1': 'value5_1',
                    'name5_2': 'value5_2',
                },
                'targets': ['host1:5555', 'host2:5555'],
            },
            {
                'labels': {
                    '__shard': 'shard3',
                    'service': 'service2',
                    'project': 'project3',
                    'farm': 'farm3',
                    '__farm_source': '',
                    'job': 'exporter6',
                    '__scheme__': 'http',
                    '__metrics_path__': '/path6',
                },
                'targets': ['host1:6666', 'host2:6666'],
            },
        ])

    def test_create_config_for_service_and_project(self):
        service = models.Service.objects.get(name='service1')
        project = models.Project.objects.get(name='project2')
        config = prometheus.create_config(service, project)
        self.assertEqual(config, [
            {
                'labels': {
                    '__shard': 'shard2',
                    'service': 'service1',
                    'project': 'project2',
                    'farm': 'farm2',
                    '__farm_source': '',
                    'job': 'exporter3',
                    '__scheme__': 'http',
                    '__metrics_path__': '/path3',
                    'name3_1': 'value3_1',
                    'name3_2': 'value3_2',
                },
                'targets': ['host1:3333', 'host2:3333'],
            },
            {
                'labels': {
                    '__shard': 'shard2',
                    'service': 'service1',
                    'project': 'project2',
                    'farm': 'farm2',
                    '__farm_source': '',
                    'job': 'exporter4',
                    '__scheme__': 'http',
                    'name4_1': 'value4_1',
                    'name4_2': 'value4_2',
                },
                'targets': ['host1:4444', 'host2:4444'],
            },
        ])

    @staticmethod
    def __create_services(services):
        for service_data in services:
            owner = service_data['owner']
            service = models.Service.objects.create(name=service_data['name'], owner=owner)
            for project_data in service_data['projects']:
                shard = models.Shard.objects.create(name=project_data['shard']['name'])
                if 'farm' in project_data:
                    farm = models.Farm.objects.create(name=project_data['farm']['name'])
                    for host_name in project_data['farm']['hosts']:
                        models.Host.objects.create(name=host_name, farm=farm)
                    project = models.Project.objects.create(name=project_data['name'], owner=owner, service=service,
                                                            shard=shard, farm=farm)
                else:
                    project = models.Project.objects.create(name=project_data['name'], owner=owner, service=service,
                                                            shard=shard)
                for exporter_data in project_data['exporters']:
                    exporter = models.Exporter.objects.create(job=exporter_data['job'], port=exporter_data['port'],
                                                              path=exporter_data['path'],
                                                              enabled=exporter_data['enabled'], project=project)
                    for name, value, *is_parameter in exporter_data['labels']:
                        models.ExporterLabel.objects.create(name=name, value=value, is_parameter=bool(is_parameter),
                                                            exporter=exporter)
