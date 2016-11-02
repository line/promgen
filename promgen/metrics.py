import json
import logging

from django.db.models import F

from promgen import models

logger = logging.getLogger(__name__)


class Gauge(object):
    type = 'gauge'

    @property
    def samples(self):
        yield 'promgen_' + self.name, [], float(self.collect())


class Counter(object):
    type = 'counter'

    @property
    def samples(self):
        for stat in self.collect:
            yield 'promgen_' + self.name, json.loads(stat.labels), stat.value

    @classmethod
    def inc(cls, labels, value=1):
        try:
            try:
                stat = models.Stat.objects.get(key=cls.name, labels=json.dumps(labels, sort_keys=True))
                stat.value = F('value') + value
                stat.save()
            except models.Stat.DoesNotExist:
                models.Stat.objects.create(
                    key=cls.name,
                    labels=json.dumps(labels, sort_keys=True),
                    value=value
                )
        except:
            logger.exception('Error recording stat')


class Farms(Gauge):
    name = 'farms'
    documentation = 'Number of registered farms'
    collect = models.Farm.objects.count


class Rules(Gauge):
    name = 'rules'
    documentation = 'Number of registered rules'
    collect = models.Rule.objects.count


class Projects(Gauge):
    name = 'projects'
    documentation = 'Number of registered projects'
    collect = models.Project.objects.count


class Services(Gauge):
    name = 'services'
    documentation = 'Number of registered services'
    collect = models.Service.objects.count


class Senders(Gauge):
    name = 'senders'
    documentation = 'Number of registered senders'
    collect = models.Sender.objects.count


class Exporters(Gauge):
    name = 'exporters'
    documentation = 'Number of registered exporters'
    collect = models.Exporter.objects.count


class AlertsSent(Counter):
    name = 'alerts_sent'
    documentation = ''
    collect = models.Stat.objects.filter(key='alerts_sent')


class AlertsError(Counter):
    name = 'alerts_error'
    documentation = ''
    collect = models.Stat.objects.filter(key='alerts_error')


class MetricsRegistry(object):
    def collect():
        yield Farms()
        yield Rules()
        yield Projects()
        yield Services()
        yield Senders()
        yield Exporters()
        yield AlertsSent()
        yield AlertsError()
