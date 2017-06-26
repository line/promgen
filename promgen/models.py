# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import json
import logging

from django.contrib.contenttypes.fields import (GenericForeignKey,
                                                GenericRelation)
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models, transaction
from django.forms.models import model_to_dict
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.text import slugify

import promgen.templatetags.promgen as macro
from promgen import plugins
from promgen.shortcuts import resolve_domain

FARM_DEFAULT = 'default'
logger = logging.getLogger(__name__)

alphanumeric = RegexValidator(r'^[0-9a-zA-Z_]*$', 'Only alphanumeric characters are allowed.')


class DynamicParent(models.Model):
    class Meta:
        abstract = True

    @classmethod
    def create(cls, obj, **kwargs):
        return cls.objects.create(
            object_id=obj.id,
            content_type_id=ContentType.objects.get_for_model(obj).id,
            **kwargs
        )

    @classmethod
    def filter(cls, obj, **kwargs):
        return cls.objects.filter(
            object_id=obj.id,
            content_type_id=ContentType.objects.get_for_model(obj).id,
            **kwargs
        )

    @classmethod
    def get_or_create(cls, **kwargs):
        if 'obj' in kwargs:
            obj = kwargs.pop('obj')
            kwargs['object_id'] = obj.id
            kwargs['content_type_id'] = ContentType.objects.get_for_model(obj).id
        if 'defaults' in kwargs and 'obj' in kwargs['defaults']:
            obj = kwargs['defaults'].pop('obj')
            kwargs['defaults']['object_id'] = obj.id
            kwargs['defaults']['content_type_id'] = ContentType.objects.get_for_model(obj).id

        return cls.objects.get_or_create(**kwargs)


class Sender(DynamicParent):
    sender = models.CharField(max_length=128)
    value = models.CharField(max_length=128)
    alias = models.CharField(max_length=128, blank=True)

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, limit_choices_to=(
        models.Q(app_label='promgen', model='project') | models.Q(app_label='promgen', model='service'))
    )
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    def show_value(self):
        if self.alias:
            return self.alias
        return self.value

    show_value.short_description = 'Value'

    def __str__(self):
        return '{}:{}'.format(self.sender, self.show_value())

    @classmethod
    def plugins(cls):
        for entry in plugins.notifications():
            try:
                yield entry.module_name, entry.load()
            except ImportError:
                logger.warning('Error importing %s', entry.module_name)


class Shard(models.Model):
    name = models.CharField(max_length=128, unique=True)
    url = models.URLField(max_length=256)

    class Meta:
        ordering = ['name']

    def get_absolute_url(self):
        return reverse('shard-detail', kwargs={'pk': self.pk})

    def __str__(self):
        return self.name


class Service(models.Model):
    name = models.CharField(max_length=128, unique=True)
    notifiers = GenericRelation(Sender)
    shard = models.ForeignKey('Shard', on_delete=models.CASCADE)

    class Meta:
        ordering = ['shard', 'name']

    def get_absolute_url(self):
        return reverse('service-detail', kwargs={'pk': self.pk})

    def __str__(self):
        return '{} » {}'.format(self.shard.name, self.name)

    @classmethod
    def default(cls, service_name='Default', shard_name='Default'):
        shard, created = Shard.objects.get_or_create(
            name=shard_name
        )
        if created:
            logger.info('Created default shard')

        service, created = cls.objects.get_or_create(
            name=service_name,
            defaults={'shard': shard}
        )
        if created:
            logger.info('Created default service')
        return service

    @property
    def check_notifiers(self):
        if self.notifiers.count() > 0:
            return True
        for project in self.project_set.all():
            if project.notifiers.count() == 0:
                return False
        return True


class Project(models.Model):
    name = models.CharField(max_length=128, unique=True)
    service = models.ForeignKey('Service', on_delete=models.CASCADE)
    farm = models.ForeignKey('Farm', blank=True, null=True, on_delete=models.SET_NULL)
    notifiers = GenericRelation(Sender)

    class Meta:
        ordering = ['name']

    def get_absolute_url(self):
        return reverse('project-detail', kwargs={'pk': self.pk})

    def __str__(self):
        return '{} » {}'.format(self.service, self.name)


class Farm(models.Model):
    name = models.CharField(max_length=128)
    source = models.CharField(max_length=128)

    class Meta:
        ordering = ['name']
        unique_together = (('name', 'source',))

    def get_absolute_url(self):
        return reverse('farm-detail', kwargs={'pk': self.pk})

    def refresh(self):
        current = set(host.name for host in self.host_set.all())
        for entry in plugins.discovery():
            if self.source == entry.name:
                target = set(entry.load()().fetch(self.name))

        keep = current & target
        remove = current - target
        add = target - current

        if add:
            Audit.log('Adding {} to {}'.format(add, self), self)
            Host.objects.bulk_create([
                Host(name=name, farm_id=self.id) for name in add
            ])

        if remove:
            Audit.log('Removing {} from {}'.format(add, self), self)
            Host.objects.filter(farm=self, name__in=remove).delete()


    @classmethod
    def fetch(cls, source):
        for entry in plugins.discovery():
            if entry.name == source:
                for farm in entry.load()().farms():
                    yield farm

    def __str__(self):
        return '{} ({})'.format(self.name, self.source)


class Host(models.Model):
    name = models.CharField(max_length=128)
    farm = models.ForeignKey('Farm', on_delete=models.CASCADE)

    class Meta:
        ordering = ['name']
        unique_together = (('name', 'farm'))

    def get_absolute_url(self):
        return reverse('host-detail', kwargs={'slug': self.name})

    def __str__(self):
        return '{} [{}]'.format(self.name, self.farm.name)


class Exporter(models.Model):
    job = models.CharField(max_length=128)
    port = models.IntegerField()
    path = models.CharField(max_length=128, blank=True)
    project = models.ForeignKey('Project', on_delete=models.CASCADE)
    enabled = models.BooleanField(default=True)

    class Meta:
        ordering = ['job', 'port']
        unique_together = (('job', 'port', 'project'))

    def __str__(self):
        return '{}:{}:{} ({})'.format(self.job, self.port, self.path, self.project)

    def get_absolute_url(self):
        return reverse('project-detail', kwargs={'pk': self.project.pk})


class URL(models.Model):
    url = models.URLField(max_length=256)
    project = models.ForeignKey('Project', on_delete=models.CASCADE)

    class Meta:
        ordering = ['project__service', 'project', 'url']

    def __str__(self):
        return '{} [{}]'.format(self.project, self.url)


def validate_json_or_empty(value):
    if value == '':
        return
    try:
        json.loads(value)
    except:
        raise ValidationError('Requires json value')


class Rule(models.Model):
    name = models.CharField(max_length=128, unique=True, validators=[alphanumeric])
    clause = models.TextField()
    duration = models.CharField(max_length=128, choices=[
        ('1s', '1s'),
        ('1m', '1m'),
        ('5m', '5m'),
    ])
    service = models.ForeignKey('Service', on_delete=models.CASCADE)
    enabled = models.BooleanField(default=True)
    parent = models.ForeignKey(
        'Rule',
        null=True,
        related_name='overrides',
        on_delete=models.SET_NULL
    )

    class Meta:
        ordering = ['service', 'name']

    @cached_property
    def labels(self):
        return {obj.name: obj.value for obj in self.rulelabel_set.all()}

    def add_label(self, name, value):
        return RuleLabel.objects.get_or_create(rule=self, name=name, value=value)

    def add_annotation(self, name, value):
        return RuleAnnotation.objects.get_or_create(rule=self, name=name, value=value)

    @cached_property
    def annotations(self):
        _annotations = {obj.name: obj.value for obj in self.ruleannotation_set.all()}
        _annotations['rule'] = resolve_domain('rule-edit', pk=self.pk)
        return _annotations

    def __str__(self):
        return '{} [{}]'.format(self.name, self.service.name)

    def get_absolute_url(self):
        return reverse('rule-edit', kwargs={'pk': self.pk})

    def copy_to(self, service):
        '''
        Make a copy under a new service

        It's important that we set pk to None so a new object is created, but we
        also need to ensure the new name is unique by appending some unique data
        to the end of the name
        '''
        with transaction.atomic():
            # First check to see if this rule is already overwritten
            for rule in Rule.objects.filter(parent_id=self.pk, service_id=service.id):
                return rule

            orig_pk = self.pk
            self.pk = None
            self.parent_id = orig_pk
            self.name = '{}_{}'.format(self.name, slugify(service.name)).replace('-', '_')
            self.service = service
            self.enabled = False
            self.clause = self.clause.replace(macro.EXCLUSION_MACRO, 'service="{}"'.format(service.name))
            self.save()

            # Add a service label to our new rule, to help ensure notifications
            # get routed to the service we expect
            self.add_label('service', service.name)

            for label in RuleLabel.objects.filter(rule_id=orig_pk):
                # Skip service labels from our previous rule
                if label.name in ['service']:
                    logger.debug('Skipping %s: %s', label.name, label.value)
                    continue
                logger.debug('Copying %s to %s', label, self)
                label.pk = None
                label.rule = self
                label.save()

            for annotation in RuleAnnotation.objects.filter(rule_id=orig_pk):
                logger.debug('Copying %s to %s', annotation, self)
                annotation.pk = None
                annotation.rule = self
                annotation.save()

        return self


class RuleLabel(models.Model):
    name = models.CharField(max_length=128)
    value = models.CharField(max_length=128)
    rule = models.ForeignKey('Rule', on_delete=models.CASCADE)


class RuleAnnotation(models.Model):
    name = models.CharField(max_length=128)
    value = models.TextField()
    rule = models.ForeignKey('Rule', on_delete=models.CASCADE)


class Audit(models.Model):
    body = models.TextField()
    created = models.DateTimeField()
    data = models.TextField(blank=True)
    old = models.TextField(blank=True)

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True)
    object_id = models.PositiveIntegerField(default=0)
    content_object = GenericForeignKey('content_type', 'object_id')

    @property
    def hilight(self):
        if self.body.startswith('Created'):
            return 'success'
        if self.body.startswith('Updated'):
            return 'warning'
        if self.body.startswith('Deleted'):
            return 'danger'
        return ''

    @classmethod
    def log(cls, body, instance=None, old=None, **kwargs):
        kwargs['body'] = body
        kwargs['created'] = timezone.now()

        if instance:
            kwargs['content_type'] = ContentType.objects.get_for_model(instance)
            kwargs['object_id'] = instance.id
            kwargs['data'] = json.dumps(model_to_dict(instance), sort_keys=True)
        if old:
            kwargs['old'] = json.dumps(model_to_dict(old), sort_keys=True)

        return cls.objects.create(**kwargs)


class Prometheus(models.Model):
    shard = models.ForeignKey('Shard', on_delete=models.CASCADE)
    host = models.CharField(max_length=128)
    port = models.IntegerField()

    def __str__(self):
        return '{}:{}'.format(self.host, self.port)

    class Meta:
        ordering = ['shard', 'host']
        unique_together = (('host', 'port'))
        verbose_name_plural = 'prometheis'
