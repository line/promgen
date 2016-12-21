import collections
import datetime
import json
import logging
import subprocess
import tempfile
from urllib.parse import urljoin

import requests
from atomicwrites import atomic_write
from django.conf import settings
from django.template.loader import render_to_string

from promgen import models

logger = logging.getLogger(__name__)


def check_rules(rules):
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf8') as fp:
        logger.debug('Rendering to %s', fp.name)
        fp.write(render_rules(rules))
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


def notify(target):
    logger.debug('Sending notifications to %s', target)
    for target in settings.PROMGEN[target].get('notify', []):
        try:
            requests.post(target).raise_for_status()
        except Exception as e:
            logger.error('%s while notifying %s', e, target)


def render_urls():
    urls = collections.defaultdict(list)
    for url in models.URL.objects.all():
        urls[(
            url.project.name, url.project.service.name,
        )].append(url.url)

    data = [{'labels': {'project': k[0], 'service': k[1]}, 'targets': v} for k, v in urls.items()]
    return json.dumps(data, indent=2, sort_keys=True)


def write_urls():
    with atomic_write(settings.PROMGEN['url_writer']['path'], overwrite=True) as fp:
        fp.write(render_urls())
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
            'project': exporter.project.name,
            'service': exporter.project.service.name,
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


def write_config():
    with atomic_write(settings.PROMGEN['config_writer']['path'], overwrite=True) as fp:
        fp.write(render_config())
    reload_prometheus()


def write_rules():
    with atomic_write(settings.PROMGEN['rule_writer']['rule_path'], overwrite=True) as fp:
        fp.write(render_rules())
    reload_prometheus()


def reload_prometheus():
    target = urljoin(settings.PROMGEN['prometheus']['url'], '/-/reload')
    try:
        requests.post(target).raise_for_status()
    except Exception as e:
        logger.error('%s while notifying %s', e, target)


def import_config(config):
    counters = collections.defaultdict(int)
    for entry in config:
        service, created = models.Service.objects.get_or_create(
            name=entry['labels']['service'],
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
    requests.post(url, json=data).raise_for_status()
