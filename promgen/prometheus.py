import json
import logging
import subprocess
import tempfile

import requests
from django.conf import settings
from django.template.loader import render_to_string

from promgen import models

logger = logging.getLogger(__name__)


def check_rules(rules):
    with tempfile.NamedTemporaryFile() as fp:
        logger.debug('Rendering to %s', fp.name)
        fp.write(render_to_string('promgen/prometheus.rule', {'rules': rules}))
        fp.flush()

        subprocess.check_call([
            settings.PROMGEN['rule_writer']['promtool_path'],
            'check-rules',
            fp.name
        ])


def render_rules():
    return render_to_string('promgen/prometheus.rule', {'rules': models.Rule.objects.all()})


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
    with open(settings.PROMGEN['config_writer']['path'], 'w+b') as fp:
        fp.write(render_config())
    for target in settings.PROMGEN['config_writer'].get('notify', []):
        try:
            requests.post(target).raise_for_status()
        except Exception, e:
            logger.error('%s while notifying %s', e, target)


def write_rules():
    with open(settings.PROMGEN['rule_writer']['rule_path'], 'w+b') as fp:
        fp.write(render_rules())
    for target in settings.PROMGEN['rule_writer'].get('notify', []):
        try:
            requests.post(target).raise_for_status()
        except Exception, e:
            logger.error('%s while notifying %s', e, target)


def reload_prometheus():
    target = '{}/-/reload'.format(settings.PROMGEN['prometheus']['url'])
    try:
        requests.post(target).raise_for_status()
    except Exception, e:
        logger.error('%s while notifying %s', e, target)
