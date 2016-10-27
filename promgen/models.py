import datetime
import json

from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from pkg_resources import working_set

FARM_DEFAULT = 'default'


class Service(models.Model):
    name = models.CharField(max_length=128, unique=True)

    class Meta:
        ordering = ['name']

    def get_absolute_url(self):
        return reverse('service-detail', kwargs={'pk': self.pk})

    def __str__(self):
        return self.name


class Project(models.Model):
    name = models.CharField(max_length=128, unique=True)
    service = models.ForeignKey('Service', on_delete=models.CASCADE)
    farm = models.ForeignKey('Farm', blank=True, null=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ['name']

    def get_absolute_url(self):
        return reverse('project-detail', kwargs={'pk': self.pk})

    def __str__(self):
        return '{} [{}]'.format(self.name, self.service.name)


class Sender(models.Model):
    project = models.ForeignKey('Project', on_delete=models.CASCADE)
    sender = models.CharField(max_length=128)
    value = models.CharField(max_length=128)
    password = models.BooleanField(default=False)


class Farm(models.Model):
    name = models.CharField(max_length=128, unique=True)
    source = models.CharField(max_length=128)

    class Meta:
        ordering = ['name']

    def refresh(self):
        remaining = [host.name for host in self.host_set.all()]
        keep = []
        create = []

        for entry in working_set.iter_entry_points('promgen.server'):
            if self.source == entry.name:
                for host in entry.load().fetch(self.name):
                    if host in remaining:
                        keep.append(host)
                        remaining.remove(host)
                    else:
                        keep.append(host)
                        create.append(host)
                        Host.objects.create(name=host, farm=self)

        if remaining:
            Host.objects.filter(farm=self, name__in=remaining).delete()

    @classmethod
    def fetch(cls, source):
        for entry in working_set.iter_entry_points('promgen.server'):
            if entry.name == source:
                for farm in entry.load().farms():
                    yield farm

    def __str__(self):
        return '{} ({})'.format(self.name, self.source)


class Host(models.Model):
    name = models.CharField(max_length=128)
    farm = models.ForeignKey('Farm', on_delete=models.CASCADE)

    class Meta:
        ordering = ['name']
        unique_together = (('name', 'farm'))

    def __str__(self):
        return '{} [{}]'.format(self.name, self.farm.name)


class Exporter(models.Model):
    job = models.CharField(max_length=128)
    port = models.IntegerField()
    path = models.CharField(max_length=128, blank=True)
    project = models.ForeignKey('Project', on_delete=models.CASCADE)

    class Meta:
        ordering = ['job']
        unique_together = (('job', 'port', 'project'))

    def __str__(self):
        return '{}:{}:{} ({})'.format(self.job, self.port, self.path, self.project)


def validate_json_or_empty(value):
    if value == '':
        return
    try:
        json.loads(value)
    except:
        raise ValidationError('Requires json value')


class Rule(models.Model):
    name = models.CharField(max_length=128, unique=True)
    clause = models.TextField()
    duration = models.CharField(max_length=128, choices=[
        ('1s', '1s'),
        ('1m', '1m'),
        ('5m', '5m'),
    ])
    labels = models.TextField(validators=[validate_json_or_empty])
    annotations = models.TextField(validators=[validate_json_or_empty])
    service = models.ForeignKey('Service', on_delete=models.CASCADE)

    class Meta:
        ordering = ['name']


class Audit(models.Model):
    body = models.TextField()
    created = models.DateTimeField()

    @classmethod
    def log(cls, body):
        return cls.objects.create(body=body, created=datetime.datetime.utcnow())
