from unittest import mock
from django.test import Client

from promgen import models
from promgen.tests import PromgenTest


class ExporterFormTest(PromgenTest):
    __COMMON_REQUEST_DATA = {
        "job": "blackbox",
        "port": "9115",
        "path": "/probe",
        "scheme": "http",
        "enabled": "on",
        "form-TOTAL_FORMS": "8",
        "form-INITIAL_FORMS": "0",
        "form-MIN_NUM_FORMS": "0",
        "form-MAX_NUM_FORMS": "8",
    }
    fixtures = ['testcases.yaml']

    @mock.patch("django.dispatch.dispatcher.Signal.send")
    def setUp(self, mock_signal):
        self.user = self.add_force_login(id=999, username="Tester")
        self.client = Client()
        self.client.force_login(self.user)

    def test_create_with_valid_data(self):
        response = self.client.post('/project/1/exporter', {**self.__COMMON_REQUEST_DATA, **{
            "form-0-name": "name1",
            "form-0-value": "value1",
            "form-1-name": "name2",
            "form-1-value": "value2",
            "form-2-name": "name2",
            "form-2-value": "param",
            "form-2-is_parameter": "on",
        }})
        exporter = models.Exporter.objects.first()

        self.assertEqual(response.status_code, 302)
        self.assertEqual('/project/1', response.headers['Location'])
        self.assertIsNotNone(exporter)
        self.assertEqual('blackbox', exporter.job)
        self.assertEqual(9115, exporter.port)
        self.assertEqual(exporter.exporterlabel_set.all().count(), 3)
        self.assertEqual('value1', exporter.exporterlabel_set.get(name__exact='name1').value)
        self.assertEqual('value2', exporter.exporterlabel_set.get(name__exact='name2', is_parameter__exact=False).value)
        self.assertEqual('param', exporter.exporterlabel_set.get(name__exact='name2', is_parameter__exact=True).value)
        self.assertTrue(exporter.exporterlabel_set.get(name__exact='name2', is_parameter__exact=True).is_parameter)

    def test_create_with_duplicated_labels_names(self):
        response = self.client.post('/project/1/exporter', {**self.__COMMON_REQUEST_DATA, **{
            "form-0-name": "name1",
            "form-0-value": "value1",
            "form-1-name": "name1",
            "form-1-value": "value2",
        }})
        exporter = models.Exporter.objects.first()

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(exporter)
