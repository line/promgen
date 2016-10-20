from __future__ import unicode_literals

import datetime
import json

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from pkg_resources import working_set


class Service(models.Model):
    name = models.CharField(max_length=128, unique=True)

    def __str__(self):
        return self.name


class Project(models.Model):
    name = models.CharField(max_length=128, unique=True)
    service = models.ForeignKey('Service', on_delete=models.CASCADE)
    farm = models.ForeignKey('Farm', blank=True, null=True)

    def __str__(self):
        return '{} [{}]'.format(self.name, self.service.name)


class Sender(models.Model):
    project = models.ForeignKey('Project', on_delete=models.CASCADE)
    sender = models.CharField(max_length=128, choices=[
        (entry.module_name, entry.module_name) for entry in working_set.iter_entry_points('promgen.sender')
    ])
    value = models.CharField(max_length=128)


class Farm(models.Model):
    name = models.CharField(max_length=128, unique=True)
    source = models.CharField(max_length=128)

    def refresh(self):
        remaining = [host.name for host in self.host_set.all()]
        keep = []

        for entry in working_set.iter_entry_points('promgen.server'):
            if self.source == entry.name:
                for host in entry.load().fetch(self.name):
                    if host in remaining:
                        keep.append(host)
                        remaining.remove(host)
                    else:
                        keep.append(host)
                        Host.objects.create(name=host, farm=self)

        if remaining:
            remove = Host.objects.get(farm=self, name__in=remaining)
            remove.delete()

    @classmethod
    def fetch(cls, source):
        for entry in working_set.iter_entry_points('promgen.server'):
            if entry.name == source:
                for farm in entry.load().farms():
                    yield farm


    def __str__(self):
        return self.name


class Host(models.Model):
    name = models.CharField(max_length=128)
    farm = models.ForeignKey('Farm', on_delete=models.CASCADE)

    class Meta:
        unique_together = (('name', 'farm'))

    def __str__(self):
        return '{} [{}]'.format(self.name, self.farm.name)


class Exporter(models.Model):
    job = models.CharField(max_length=128)
    port = models.IntegerField()
    path = models.CharField(max_length=128)
    project = models.ForeignKey('Project', on_delete=models.CASCADE)

    class Meta:
        unique_together = (('job', 'port', 'project'))


def validate_json_or_empty(value):
    if value == '':
        return
    try:
        json.loads(value)
    except:
        raise ValidationError('Requires json value')


class Rule(models.Model):
    name = models.CharField(max_length=128, unique=True)
    clause = models.CharField(max_length=128)
    duration = models.CharField(max_length=128, choices=[
        ('1s', '1s'),
        ('1m', '1m'),
        ('5m', '5m'),
    ])
    labels = models.TextField(validators=[validate_json_or_empty])
    annotations = models.TextField(validators=[validate_json_or_empty])
    service = models.ForeignKey('Service', on_delete=models.CASCADE)


class Audit(models.Model):
    body = models.TextField()
    created = models.DateTimeField()

    @classmethod
    def log(cls, body):
        return cls.objects.create(body=body, created=datetime.datetime.utcnow())


class Setting(models.Model):
    key = models.CharField(max_length=128, primary_key=True)
    value = models.CharField(max_length=128)


@receiver(post_save)
def my_handler(sender, instance, created, **kwargs):
    if sender is not Audit:
        if created:
            Audit.log('Updating instance of %s' % instance)
        else:
            Audit.log('Created instance of %s' % instance)
