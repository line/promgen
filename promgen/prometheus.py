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
        fp.write(render_to_string('promgen/rules.txt', {'rules': rules}))
        fp.flush()

        subprocess.check_call([
            settings.PROMGEN['rule_writer']['promtool_path'],
            'check-rules',
            fp.name
        ])


def render_rules():
    return render_to_string('promgen/rules.txt', {'rules': models.Rule.objects.all()})


def render_config():
    data = []
    for exporter in models.Exporter.objects.all():
        if not exporter.project.farm:
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


def write_rules():
    with open(settings.PROMGEN['rule_writer']['rule_path'], 'w+b') as fp:
        fp.write(render_config())


def reload_prometheus():
    response = requests.post('{}/-/reload'.format(settings.PROMGEN['prometheus']['url']))
    response.raise_for_status()
