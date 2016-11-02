from promgen import models


class Gauge(object):
    type = 'gauge'

    @property
    def samples(self):
        yield 'promgen_' + self.name, [], float(self.collect())


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


class MetricsRegistry(object):
    def collect():
        yield Farms()
        yield Rules()
        yield Projects()
        yield Services()
        yield Senders()
        yield Exporters()
