import collections
import datetime
import json
import logging
import re
import subprocess
import tempfile
from urllib.parse import urljoin

import pytz
from atomicwrites import atomic_write
from django.conf import settings
from django.template.loader import render_to_string

from promgen import models, util
from promgen.celery import app as celery

logger = logging.getLogger(__name__)


def check_rules(rules):
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf8') as fp:
        logger.debug('Rendering to %s', fp.name)
        # Normally we wouldn't bother saving a copy to a variable here and would
        # leave it in the fp.write() call, but saving a copy in the variable
        # means we can see the rendered output in a Sentry stacktrace
        rendered = render_rules(rules)
        fp.write(rendered)
        fp.flush()

        subprocess.check_call([
            settings.PROMGEN['rule_writer']['promtool_path'],
            'check-rules',
            fp.name
        ])


def render_rules(rules=None):
    if rules is None:
        rules = models.Rule.objects.filter(enabled=True)
    return render_to_string('promgen/prometheus.rule', {'rules': rules})


def render_urls():
    urls = collections.defaultdict(list)
    for url in models.URL.objects.all():
        urls[(
            url.project.name, url.project.service.name,
        )].append(url.url)

    data = [{'labels': {'project': k[0], 'service': k[1]}, 'targets': v} for k, v in urls.items()]
    return json.dumps(data, indent=2, sort_keys=True)


@celery.task
def write_urls(path=None, reload=True):
    if path is None:
        path = settings.PROMGEN['url_writer']['path']
    with atomic_write(path, overwrite=True) as fp:
        fp.write(render_urls())
    if reload:
        reload_prometheus()


def render_config(service=None, project=None):
    data = []
    for exporter in models.Exporter.objects.all():
        if not exporter.project.farm:
            continue
        if service and exporter.project.service.name != service.name:
            continue
        if project and exporter.project.name != project.name:
            continue

        labels = {
            '__shard': exporter.project.service.shard.name,
            'service': exporter.project.service.name,
            'project': exporter.project.name,
            'farm': exporter.project.farm.name,
            '__farm_source': exporter.project.farm.source,
            'job': exporter.job,
        }
        if exporter.path:
            labels['__metrics_path__'] = exporter.path

        hosts = []
        for host in models.Host.objects.filter(farm=exporter.project.farm):
            hosts.append('{}:{}'.format(host.name, exporter.port))

        data.append({
            'labels': labels,
            'targets': hosts,
        })
    return json.dumps(data, indent=2, sort_keys=True)


@celery.task
def write_config(path=None, reload=True):
    if path is None:
        path = settings.PROMGEN['config_writer']['path']
    with atomic_write(path, overwrite=True) as fp:
        fp.write(render_config())
    if reload:
        reload_prometheus()


@celery.task
def write_rules(path=None, reload=True):
    if path is None:
        path = settings.PROMGEN['rule_writer']['path']
    with atomic_write(path, overwrite=True) as fp:
        fp.write(render_rules())
    if reload:
        reload_prometheus()


@celery.task
def reload_prometheus():
    from promgen.signals import post_reload
    target = urljoin(settings.PROMGEN['prometheus']['url'], '/-/reload')
    response = util.post(target)
    post_reload.send(response)


def import_rules(config, default_service=None):
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

        if default_service:
            service = default_service
        else:
            try:
                service = models.Service.objects.get(name=labels.get('service', 'Default'))
            except models.Service.DoesNotExist:
                service = models.Service.default()

        rule, created = models.Rule.objects.get_or_create(
            name=tokens['ALERT'],
            defaults={
                'clause': tokens['IF'],
                'duration': tokens['FOR'],
                'service': service,
            }
        )

        if created:
            counters['Rules'] += 1
            for k, v in labels.items():
                models.RuleLabel.objects.create(name=k, value=v, rule=rule)
                counters['Labels'] += 1
            for k, v in annotations.items():
                models.RuleAnnotation.objects.create(name=k, value=v, rule=rule)
                counters['Annotations'] += 1

    return dict(counters)


def import_config(config):
    counters = collections.defaultdict(int)
    for entry in config:
        shard, created = models.Shard.objects.get_or_create(
            name=entry['labels'].get('__shard', 'Default')
        )
        if created:
            counters['Shard'] += 1

        service, created = models.Service.objects.get_or_create(
            name=entry['labels']['service'],
            defaults={'shard': shard}
        )
        if created:
            counters['Service'] += 1

        farm, created = models.Farm.objects.get_or_create(
            name=entry['labels']['farm'],
            defaults={'source': entry['labels'].get('__farm_source', 'pmc')}
        )
        if created:
            counters['Farm'] += 1

        project, created = models.Project.objects.get_or_create(
            name=entry['labels']['project'],
            service=service,
            defaults={'farm': farm}
        )
        if created:
            counters['Project'] += 1

        if not project.farm:
            project.farm = farm
            project.save()

        for target in entry['targets']:
            target, port = target.split(':')
            host, created = models.Host.objects.get_or_create(
                name=target,
                farm_id=farm.id,
            )

            if created:
                counters['Host'] += 1

            exporter, created = models.Exporter.objects.get_or_create(
                job=entry['labels']['job'],
                port=port,
                project=project,
                path=entry['labels'].get('__metrics_path__', '')
            )

            if created:
                counters['Exporter'] += 1

    return dict(counters)


def mute(duration, labels):
    '''
    Post a silence message to Alert Manager
    Duration should be sent in a format like 1m 2h 1d etc
    '''
    start = datetime.datetime.now(datetime.timezone.utc)

    if duration.lower().endswith('m'):
        end = start + datetime.timedelta(minutes=int(duration[:-1]))
    elif duration.lower().endswith('h'):
        end = start + datetime.timedelta(hours=int(duration[:-1]))
    elif duration.lower().endswith('d'):
        end = start + datetime.timedelta(days=int(duration[:-1]))
    else:
        raise Exception('Unknown time modifier')

    data = {
        'comment': 'Promgen Mute',
        'createdBy': 'Promgen',
        'matchers': [{'name': name, 'value': value} for name, value in labels.items()],
        'endsAt': end.strftime('%Y-%m-%dT%H:%M:%S.000Z')
    }

    logger.debug('Sending silence for %s %s', end, data)
    url = urljoin(settings.PROMGEN['alertmanager']['url'], '/api/v1/silences')
    util.post(url, json=data).raise_for_status()


def mute_fromto(start, stop, labels):
    '''
    Post a silence message to Alert Manager
    Duration should be sent in a format like 2017-01-01 09:00
    '''
    local_timezone = pytz.timezone(settings.PROMGEN.get('timezone', 'UTC'))
    mute_start = datetime.datetime.strptime(start, '%Y-%m-%d %H:%M').replace(tzinfo=local_timezone)
    mute_stop = datetime.datetime.strptime(stop, '%Y-%m-%d %H:%M').replace(tzinfo=local_timezone)

    data = {
        'comment': 'Promgen Mute',
        'createdBy': 'Promgen',
        'matchers': [{'name': name, 'value': value} for name, value in labels.items()],
        'startsAt': mute_start.astimezone(pytz.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z'),
        'endsAt': mute_stop.astimezone(pytz.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')
    }

    logger.debug('Sending silence for %s - %s %s', start, stop, data)
    url = urljoin(settings.PROMGEN['alertmanager']['url'], '/api/v1/silences')
    util.post(url, json=data).raise_for_status()
