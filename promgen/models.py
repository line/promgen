from __future__ import unicode_literals
from django.dispatch import receiver
from pkg_resources import working_set
import datetime
from django.db import models
from django.db.models.signals import post_save


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

    def __str__(self):
        return self.name


class Host(models.Model):
    name = models.CharField(max_length=128)
    farm = models.ForeignKey('Farm', on_delete=models.CASCADE)

    unique_together = ('name', 'farm')

    def __str__(self):
        return '{} [{}]'.format(self.name, self.farm.name)


class Exporter(models.Model):
    job = models.CharField(max_length=128)
    port = models.IntegerField()
    path = models.CharField(max_length=128)
    project = models.ForeignKey('Project', on_delete=models.CASCADE)

    unique_together = ('port', 'path', 'project')


class Rule(models.Model):
    name = models.CharField(max_length=128, unique=True)
    clause = models.CharField(max_length=128)
    duration = models.CharField(max_length=128, choices=[
        ('1s', '1s'),
        ('1m', '1m'),
        ('5m', '5m'),
    ])
    labels = models.CharField(max_length=128)
    annotations = models.CharField(max_length=128)
    service = models.ForeignKey('Service', on_delete=models.CASCADE)


class Audit(models.Model):
    body = models.TextField()
    created = models.DateTimeField()

    @classmethod
    def log(cls, body):
        return cls.objects.create(body=body, created=datetime.datetime.utcnow())


@receiver(post_save)
def my_handler(sender, instance, created, **kwargs):
    if sender is not Audit:
        if created:
            Audit.log('Updating instance of %s' % instance)
        else:
            Audit.log('Created instance of %s' % instance)
