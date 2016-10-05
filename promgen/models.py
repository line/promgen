from __future__ import unicode_literals

from django.db import models


class Service(models.Model):
    name = models.CharField(max_length=128, unique=True)

    def __str__(self):
        return self.name


class Project(models.Model):
    name = models.CharField(max_length=128, unique=True)
    service = models.ForeignKey('Service', on_delete=models.CASCADE)
    farm = models.ForeignKey('Farm', blank=True, null=True)

    def __str__(self):
        return '{}:{}'.format(self.service.name, self.name)


class Farm(models.Model):
    name = models.CharField(max_length=128, unique=True)
    source = models.CharField(max_length=128)

    def __str__(self):
        return self.name


class Host(models.Model):
    name = models.CharField(max_length=128)
    farm = models.ForeignKey('Farm', on_delete=models.CASCADE)

    unique_together = ('name', 'farm')


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
