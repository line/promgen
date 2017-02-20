from unittest import mock
from django.test import TestCase

from promgen import models, prometheus


_RULES = '''
# Service: Service 1
# Service URL: /service/1/
ALERT RuleName
  IF up==0
  FOR 1s
  LABELS {severity="severe"}
  ANNOTATIONS {service="http://example.com/service/1/", summary="Test case"}


'''.lstrip()


class RuleTest(TestCase):
    @mock.patch('django.db.models.signals.post_save', mock.Mock())
    def setUp(self):
        self.shard = models.Shard.objects.create(name='Shard 1')
        self.service = models.Service.objects.create(id=1, name='Service 1', shard=self.shard)
        self.rule = models.Rule.objects.create(
            name='RuleName',
            clause='up==0',
            duration='1s',
            service=self.service
        )
        models.RuleLabel.objects.create(name='severity', value='severe', rule=self.rule)
        models.RuleAnnotation.objects.create(name='summary', value='Test case', rule=self.rule)

    @mock.patch('django.db.models.signals.post_save')
    def test_write(self, mock_render):
        result = prometheus.render_rules()
        self.assertEqual(result, _RULES)
