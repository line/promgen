import collections
import json
import logging
import subprocess
import tempfile

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


def render_urls():
    urls = collections.defaultdict(list)
    for url in models.URL.objects.all():
        urls[(
            url.project.name, url.project.service.name,
        )].append(url.url)

    data = [{'labels': {'project': k[0], 'service': k[1]}, 'targets': v} for k, v in urls.items()]
    return json.dumps(data, indent=2, sort_keys=True)


def write_urls(notify=True):
    with atomic_write(settings.PROMGEN['url_writer']['path'], overwrite=True) as fp:
        fp.write(render_urls())
    reload_prometheus()
    if notify:
        for target in settings.PROMGEN['url_writer'].get('notify', []):
            try:
                requests.post(target).raise_for_status()
            except Exception as e:
                logger.error('%s while notifying %s', e, target)


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


def write_config(notify=True):
    with atomic_write(settings.PROMGEN['config_writer']['path'], overwrite=True) as fp:
        fp.write(render_config())
    reload_prometheus()
    if notify:
        for target in settings.PROMGEN['config_writer'].get('notify', []):
            try:
                requests.post(target).raise_for_status()
            except Exception as e:
                logger.error('%s while notifying %s', e, target)


def write_rules(notify=True):
    with atomic_write(settings.PROMGEN['rule_writer']['rule_path'], overwrite=True) as fp:
        fp.write(render_rules())
    reload_prometheus()
    if notify:
        for target in settings.PROMGEN['rule_writer'].get('notify', []):
            try:
                requests.post(target).raise_for_status()
            except Exception as e:
                logger.error('%s while notifying %s', e, target)


def reload_prometheus():
    target = '{}/-/reload'.format(settings.PROMGEN['prometheus']['url'])
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
