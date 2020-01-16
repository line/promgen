# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE
import collections
import datetime
import json
import logging
import subprocess
import tempfile
from urllib.parse import urljoin

import pytz
import yaml
from dateutil import parser

from django.core.exceptions import ValidationError
from django.utils import timezone

from promgen import models, renderers, serializers, util

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
        cmd = [util.setting("prometheus:promtool"), "check", "rules", fp.name]

        try:
            subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            raise ValidationError(rendered.decode('utf8') + e.output.decode('utf8'))


def render_rules(rules=None):
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

    return renderers.RuleRenderer().render(
        serializers.AlertRuleSerializer(rules, many=True).data
    )


def render_urls():
    urls = collections.defaultdict(list)

    for url in models.URL.objects.prefetch_related(
        "project__service",
        "project__shard",
        "project",
    ):
        urls[
            (
                url.project.name,
                url.project.service.name,
                url.project.shard.name,
                url.probe.module,
            )
        ].append(url.url)

    data = [
        {
            "labels": {
                "project": k[0],
                "service": k[1],
                "job": k[3],
                "__shard": k[2],
                "__param_module": k[3],
            },
            "targets": v,
        }
        for k, v in urls.items()
    ]
    return json.dumps(data, indent=2, sort_keys=True)


def render_config(service=None, project=None):
    data = []
    for exporter in models.Job.objects.\
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


def import_rules_v2(config, content_object=None):
    '''
    Loop through a dictionary and add rules to the database

    This assumes a dictonary in the 2.x rule format.
    See promgen/tests/examples/import.rule.yml for an example
    '''
    # If not already a dictionary, try to load as YAML
    if not isinstance(config, dict):
        config = yaml.safe_load(config)

    # If 'groups' does not exist in our config, assume that a single
    # rule is being imported (perhaps from Promgen's UI) so wrap it
    # to be the full rule format we expect
    # https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/
    # TODO In the future want to refactor this into the API itself
    if "groups" not in config:
        config = {"groups": [{"name": "Import", "rules": [config]}]}

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

            exporter, created = models.Job.objects.get_or_create(
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
        local_timezone = pytz.timezone(util.setting("timezone", "UTC"))
        for key in ['startsAt', 'endsAt']:
            kwargs[key] = local_timezone.localize(
                parser.parse(kwargs[key])
            ).isoformat()

    kwargs['matchers'] = [{
        'name': name,
        'value': value,
        'isRegex': True if value.endswith("*") else False
    } for name, value in labels.items()]

    logger.debug("Sending silence for %s", kwargs)
    url = urljoin(util.setting("alertmanager:url"), "/api/v1/silences")
    response = util.post(url, json=kwargs)
    response.raise_for_status()
    return response
