# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE
import collections
import datetime
import json
import logging
import os
import re
import subprocess
import tempfile
from urllib.parse import urljoin

import pytz
import yaml
from atomicwrites import atomic_write
from dateutil import parser
from django.conf import settings
from django.db.models import prefetch_related_objects
from django.template.loader import render_to_string
from django.utils import timezone
from django.core.exceptions import ValidationError
import promgen.templatetags.promgen as macro
from promgen import models, util
from promgen.celery import app as celery

logger = logging.getLogger(__name__)


def check_rules(rules):
    '''
    Use promtool to check to see if a rule is valid or not

    The command name changed slightly from 1.x -> 2.x but this uses promtool
    to verify if the rules are correct or not. This can be bypassed by setting
    a dummy command such as /usr/bin/true that always returns true
    '''

    with tempfile.NamedTemporaryFile(mode='w+b') as fp:
        logger.debug('Rendering to %s', fp.name)
        # Normally we wouldn't bother saving a copy to a variable here and would
        # leave it in the fp.write() call, but saving a copy in the variable
        # means we can see the rendered output in a Sentry stacktrace
        rendered = render_rules(rules)
        fp.write(rendered)
        fp.flush()

        # This command changed to be without a space in 2.x
        cmd = [settings.PROMGEN['prometheus']['promtool']]
        if settings.PROMGEN['prometheus'].get('version') == 2:
            cmd += ['check', 'rules']
        else:
            cmd += ['check-rules']
        cmd += [fp.name]

        try:
            subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            raise ValidationError(rendered.decode('utf8') + e.output.decode('utf8'))


def render_rules(rules=None, version=None):
    '''
    Render rules in a format that Prometheus understands

    :param rules: List of rules
    :type rules: list(Rule)
    :param int version: Prometheus rule format (1 or 2)
    :return: Returns rules in yaml or Prometheus v1 format
    :rtype: bytes

    This function can render in either v1 or v2 format
    We call prefetch_related_objects within this function to populate the
    other related objects that are mostly used for the sub lookups.
    '''
    if rules is None:
        rules = models.Rule.objects.filter(enabled=True)
    if version is None:
        version = settings.PROMGEN['prometheus'].get('version', 1)

    prefetch_related_objects(
        rules,
        'content_object',
        'content_type',
        'overrides__content_object',
        'overrides__content_type',
        'ruleannotation_set',
        'rulelabel_set',
    )

    # V1 format is a custom format which we render through django templates
    # See promgen/tests/examples/import.rule
    if version == 1:
        return render_to_string('promgen/prometheus.rule', {'rules': rules}).encode('utf-8')

    # V2 format is a yaml dictionary which we build and then render
    # See promgen/tests/examples/import.rule.yml
    rule_list = collections.defaultdict(list)
    for r in rules:
        rule_list[str(r.content_object)].append({
            'alert': r.name,
            'expr': macro.rulemacro(r.clause, r),
            'for': r.duration,
            'labels': r.labels,
            'annotations': r.annotations,
        })

    return yaml.safe_dump({'groups': [
        {'name': name, 'rules': rule_list[name]} for name in rule_list
    ]}, default_flow_style=False, allow_unicode=True, encoding='utf-8')


def render_urls():
    urls = collections.defaultdict(list)

    for url in models.URL.objects.prefetch_related(
            'project__farm__host_set',
            'project__farm',
            'project__service',
            'project__service',
            'project__shard',
            'project'):
        urls[(
            url.project.name, url.project.service.name, url.project.shard.name,
        )].append(url.url)

    data = [{'labels': {'project': k[0], 'service': k[1], '__shard': k[2]}, 'targets': v} for k, v in urls.items()]
    return json.dumps(data, indent=2, sort_keys=True)


@celery.task
def write_urls(path=None, reload=True, chmod=0o644):
    if path is None:
        path = settings.PROMGEN['url_writer']['path']
    with atomic_write(path, overwrite=True) as fp:
        # Set mode on our temporary file before we write and move it
        os.chmod(fp.name, chmod)
        fp.write(render_urls())
    if reload:
        reload_prometheus()


def render_config(service=None, project=None):
    data = []
    for exporter in models.Exporter.objects.\
            prefetch_related(
                'project__farm__host_set',
                'project__farm',
                'project__service',
                'project__shard',
                'project',
                ):
        if not exporter.project.farm:
            continue
        if service and exporter.project.service.name != service.name:
            continue
        if project and exporter.project.name != project.name:
            continue
        if not exporter.enabled:
            continue

        labels = {
            '__shard': exporter.project.shard.name,
            'service': exporter.project.service.name,
            'project': exporter.project.name,
            'farm': exporter.project.farm.name,
            '__farm_source': exporter.project.farm.source,
            'job': exporter.job,
        }
        if exporter.path:
            labels['__metrics_path__'] = exporter.path

        hosts = []
        for host in exporter.project.farm.host_set.all():
            hosts.append('{}:{}'.format(host.name, exporter.port))

        data.append({
            'labels': labels,
            'targets': hosts,
        })
    return json.dumps(data, indent=2, sort_keys=True)


@celery.task
def write_config(path=None, reload=True, chmod=0o644):
    if path is None:
        path = settings.PROMGEN['config_writer']['path']
    with atomic_write(path, overwrite=True) as fp:
        # Set mode on our temporary file before we write and move it
        os.chmod(fp.name, chmod)
        fp.write(render_config())
    if reload:
        reload_prometheus()


@celery.task
def write_rules(path=None, reload=True, chmod=0o644, version=None):
    if path is None:
        path = settings.PROMGEN['prometheus']['rules']
    with atomic_write(path, mode='wb', overwrite=True) as fp:
        # Set mode on our temporary file before we write and move it
        os.chmod(fp.name, chmod)
        fp.write(render_rules(version=version))
    if reload:
        reload_prometheus()


@celery.task
def reload_prometheus():
    from promgen.signals import post_reload
    target = urljoin(settings.PROMGEN['prometheus']['url'], '/-/reload')
    response = util.post(target)
    post_reload.send(response)


def import_rules_v2(config, content_object=None):
    '''
    Loop through a dictionary and add rules to the database

    This assumes a dictonary in the 2.x rule format.
    See promgen/tests/examples/import.rule.yml for an example
    '''
    counters = collections.defaultdict(int)
    for group in config['groups']:
        for r in group['rules']:
            labels = r.get('labels', {})
            annotations = r.get('annotations', {})

            defaults = {
                'clause': r['expr'],
                'duration': r['for'],
            }

            # Check our labels to see if we have a project or service
            # label set and if not, default it to a global rule
            if content_object:
                defaults['obj'] = content_object
            elif 'project' in labels:
                defaults['obj'] = models.Project.objects.get(name=labels['project'])
            elif 'service' in labels:
                defaults['obj'] = models.Service.objects.get(name=labels['service'])
            else:
                defaults['obj'] = models.Site.objects.get_current()

            rule, created = models.Rule.objects.get_or_create(
                name=r['alert'],
                defaults=defaults
            )

            if created:
                counters['Rules'] += 1
            for k, v in labels.items():
                rule.add_label(k, v)
            for k, v in annotations.items():
                rule.add_annotation(k, v)

    return dict(counters)


def import_rules_v1(config, content_object=None):
    '''
    Parse text and extract Prometheus rules

    This assumes text in the 1.x rule format.
    See promgen/tests/examples/import.rule for an example
    '''
    # Attemps to match the pattern name="value" for Prometheus labels and annotations
    RULE_MATCH = re.compile('((?P<key>\w+)\s*=\s*\"(?P<value>.*?)\")')
    counters = collections.defaultdict(int)

    def parse_prom(text):
        if not text:
            return {}
        converted = {}
        for match, key, value in RULE_MATCH.findall(text.strip().strip('{}')):
            converted[key] = value
        return converted

    tokens = {}
    rules = []
    for line in config.split('\n'):
        line = line.strip()
        if not line:
            continue
        if line.startswith('#'):
            continue

        keyword, data = line.split(' ', 1)

        if keyword != 'ALERT':
            tokens[keyword] = data
            continue

        if keyword == 'ALERT' and 'ALERT' not in tokens:
            tokens[keyword] = data
            continue

        rules.append(tokens)
        # Start building our next rule
        tokens = {keyword: data}
    # Make sure we keep our last token after parsing all lines
    rules.append(tokens)

    for tokens in rules:
        labels = parse_prom(tokens.get('LABELS'))
        annotations = parse_prom(tokens.get('ANNOTATIONS'))

        # Check our labels to see if we have a project or service
        # label set and if not, default it to a global rule
        if content_object:
            obj = content_object
        elif 'project' in labels:
            obj = models.Project.objects.get(name=labels['project'])
        elif 'service' in labels:
            obj = models.Service.objects.get(name=labels['service'])
        else:
            obj = models.Site.objects.get_current()

        rule, created = models.Rule.objects.get_or_create(
            name=tokens['ALERT'],
            defaults={
                'clause': tokens['IF'],
                'duration': tokens['FOR'],
                'obj': obj,
            }
        )

        if created:
            counters['Rules'] += 1
        for k, v in labels.items():
            rule.add_label(k, v)
        for k, v in annotations.items():
            rule.add_annotation(k, v)

    return dict(counters)


def import_rules(config, content_object=None):
    try:
        data = yaml.safe_load(config)
    except Exception as e:
        logger.debug('If we fail to parse yaml, then assume it is v1 format')
        return import_rules_v1(config, content_object)
    else:
        return import_rules_v2(data, content_object)


def import_config(config, replace_shard=None):
    counters = collections.defaultdict(list)
    skipped = collections.defaultdict(list)
    for entry in config:
        if replace_shard:
            logger.debug('Importing into shard %s', replace_shard)
            entry['labels']['__shard'] = replace_shard
        shard, created = models.Shard.objects.get_or_create(
            name=entry['labels'].get('__shard', 'Default')
        )
        if created:
            logger.debug('Created shard %s', shard)
            counters['Shard'].append(shard)
        else:
            skipped['Shard'].append(shard)

        service, created = models.Service.objects.get_or_create(
            name=entry['labels']['service'],
        )
        if created:
            logger.debug('Created service %s', service)
            counters['Service'].append(service)
        else:
            skipped['Service'].append(service)

        farm, created = models.Farm.objects.get_or_create(
            name=entry['labels']['farm'],
            defaults={'source': entry['labels'].get('__farm_source', 'pmc')}
        )
        if created:
            logger.debug('Created farm %s', farm)
            counters['Farm'].append(farm)
        else:
            skipped['Farm'].append(farm)

        project, created = models.Project.objects.get_or_create(
            name=entry['labels']['project'],
            service=service,
            shard=shard,
            defaults={'farm': farm}
        )
        if created:
            logger.debug('Created project %s', project)
            counters['Project'].append(project)
        elif project.farm != farm:
            logger.debug('Linking farm [%s] with [%s]', farm, project)
            project.farm = farm
            project.save()

        for target in entry['targets']:
            target, port = target.split(':')
            host, created = models.Host.objects.get_or_create(
                name=target,
                farm_id=farm.id,
            )

            if created:
                logger.debug('Created host %s', host)
                counters['Host'].append(host)

            exporter, created = models.Exporter.objects.get_or_create(
                job=entry['labels']['job'],
                port=port,
                project=project,
                path=entry['labels'].get('__metrics_path__', '')
            )

            if created:
                logger.debug('Created exporter %s', exporter)
                counters['Exporter'].append(exporter)

    return counters, skipped


def silence(labels, duration=None, **kwargs):
    '''
    Post a silence message to Alert Manager
    Duration should be sent in a format like 1m 2h 1d etc
    '''
    if duration:
        start = timezone.now()
        if duration.endswith('m'):
            end = start + datetime.timedelta(minutes=int(duration[:-1]))
        elif duration.endswith('h'):
            end = start + datetime.timedelta(hours=int(duration[:-1]))
        elif duration.endswith('d'):
            end = start + datetime.timedelta(days=int(duration[:-1]))
        else:
            raise ValidationError('Unknown time modifier')
        kwargs['endsAt'] = end.isoformat()
        kwargs.pop('startsAt', False)
    else:
        local_timezone = pytz.timezone(settings.PROMGEN.get('timezone', 'UTC'))
        for key in ['startsAt', 'endsAt']:
            kwargs[key] = local_timezone.localize(
                parser.parse(kwargs[key])
            ).isoformat()

    kwargs['matchers'] = [{
        'name': name,
        'value': value,
        'isRegex': True if value.endswith("*") else False
    } for name, value in labels.items()]

    logger.debug('Sending silence for %s', kwargs)
    url = urljoin(settings.PROMGEN['alertmanager']['url'], '/api/v1/silences')
    response = util.post(url, json=kwargs)
    response.raise_for_status()
    return response
