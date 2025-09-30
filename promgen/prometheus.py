# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE
import collections
import datetime
import json
import logging
import subprocess
import tempfile
from urllib.parse import urljoin

import yaml
from dateutil import parser
from django.core.exceptions import ValidationError
from django.utils import timezone

from promgen import models, renderers, serializers, util

logger = logging.getLogger(__name__)


def check_rules(rules):
    """
    Use promtool to check to see if a rule is valid or not

    The command name changed slightly from 1.x -> 2.x but this uses promtool
    to verify if the rules are correct or not. This can be bypassed by setting
    a dummy command such as /usr/bin/true that always returns true
    """

    with tempfile.NamedTemporaryFile(mode="w+b") as fp:
        logger.debug("Rendering to %s", fp.name)
        # Normally we wouldn't bother saving a copy to a variable here and would
        # leave it in the fp.write() call, but saving a copy in the variable
        # means we can see the rendered output in a Sentry stacktrace
        rendered = render_rules(rules)
        fp.write(rendered)
        fp.flush()

        # This command changed to be without a space in 2.x
        cmd = [util.setting("prometheus:promtool"), "check", "rules", fp.name]

        try:
            subprocess.check_output(cmd, stderr=subprocess.STDOUT, encoding="utf8")
        except subprocess.CalledProcessError as e:
            raise ValidationError(message=e.output + rendered.decode("utf8"))


def render_rules(rules=None):
    """
    Render rules in a format that Prometheus understands

    :param rules: List of rules
    :type rules: list(Rule)
    :param int version: Prometheus rule format (1 or 2)
    :return: Returns rules in yaml or Prometheus v1 format
    :rtype: bytes

    This function can render in either v1 or v2 format
    We call prefetch_related_objects within this function to populate the
    other related objects that are mostly used for the sub lookups.
    """
    if rules is None:
        rules = models.Rule.objects.filter(enabled=True)

    return renderers.RuleRenderer().render(serializers.AlertRuleSerializer(rules, many=True).data)


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
    for exporter in models.Exporter.objects.prefetch_related(
        "project__farm__host_set",
        "project__farm",
        "project__service",
        "project__shard",
        "project",
    ):
        if getattr(exporter.project, "farm", None) is None:
            continue
        if service and exporter.project.service.name != service.name:
            continue
        if project and exporter.project.name != project.name:
            continue
        if not exporter.enabled:
            continue

        labels = {
            "__shard": exporter.project.shard.name,
            "service": exporter.project.service.name,
            "project": exporter.project.name,
            "farm": exporter.project.farm.name,
            "__farm_source": exporter.project.farm.source,
            "job": exporter.job,
            "__scheme__": exporter.scheme,
        }
        if exporter.path:
            labels["__metrics_path__"] = exporter.path

        hosts = []
        for host in exporter.project.farm.host_set.all():
            hosts.append(f"{host.name}:{exporter.port}")

        data.append({"labels": labels, "targets": hosts})
    return json.dumps(data, indent=2, sort_keys=True)


def import_rules_v2(config, content_object=None):
    """
    Loop through a dictionary and add rules to the database

    This assumes a dictionary in the 2.x rule format.
    See promgen/tests/examples/import.rule.yml for an example
    """
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
    for group in config["groups"]:
        for r in group["rules"]:
            defaults = {
                "clause": r["expr"],
                "duration": r["for"],
                "labels": r.get("labels", {}),
                "annotations": r.get("annotations", {}),
            }

            # Check our labels to see if we have a project or service
            # label set and if not, default it to a global rule
            if content_object:
                defaults["obj"] = content_object
            elif "project" in defaults["labels"]:
                defaults["obj"] = models.Project.objects.get(name=defaults["labels"]["project"])
            elif "service" in defaults["labels"]:
                defaults["obj"] = models.Service.objects.get(name=defaults["labels"]["service"])
            else:
                defaults["obj"] = models.Site.objects.get_current()

            _, created = models.Rule.objects.get_or_create(name=r["alert"], defaults=defaults)

            if created:
                counters["Rules"] += 1

    return dict(counters)


def import_config(config, user, replace_shard=None):
    counters = collections.defaultdict(list)
    skipped = collections.defaultdict(list)
    for entry in config:
        if replace_shard:
            logger.debug("Importing into shard %s", replace_shard)
            entry["labels"]["__shard"] = replace_shard
        shard, created = models.Shard.objects.get_or_create(
            name=entry["labels"].get("__shard", "Default")
        )
        if created:
            logger.debug("Created shard %s", shard)
            counters["Shard"].append(shard)
        else:
            skipped["Shard"].append(shard)

        service, created = models.Service.objects.get_or_create(
            name=entry["labels"]["service"],
            owner=user,
        )
        if created:
            logger.debug("Created service %s", service)
            counters["Service"].append(service)
        else:
            skipped["Service"].append(service)

        project, created = models.Project.objects.get_or_create(
            name=entry["labels"]["project"],
            service=service,
            shard=shard,
            owner=user,
        )
        if created:
            logger.debug("Created project %s", project)
            counters["Project"].append(project)

        farm = models.Farm.objects.filter(project=project).first()
        created = False
        if farm:
            farm.name = entry["labels"]["farm"]
            farm.source = entry["labels"].get("__farm_source", "pmc")
            farm.save()
        else:
            farm = models.Farm.objects.create(
                name=entry["labels"]["farm"],
                source=entry["labels"].get("__farm_source", "pmc"),
                project=project,
            )
            created = True

        if created:
            logger.debug("Created farm %s", farm)
            counters["Farm"].append(farm)
        else:
            skipped["Farm"].append(farm)

        for target in entry["targets"]:
            target, port = target.split(":")
            host, created = models.Host.objects.get_or_create(
                name=target,
                farm_id=farm.id,
            )

            if created:
                logger.debug("Created host %s", host)
                counters["Host"].append(host)

            exporter, created = models.Exporter.objects.get_or_create(
                job=entry["labels"]["job"],
                port=port,
                project=project,
                path=entry["labels"].get("__metrics_path__", ""),
            )

            if created:
                logger.debug("Created exporter %s", exporter)
                counters["Exporter"].append(exporter)

    return counters, skipped


def silence(*, labels, duration=None, **kwargs):
    """
    Post a silence message to Alert Manager
    Duration should be sent in a format like 1m 2h 1d etc
    """
    # We active a timezone here, because the frontend (browser)
    # will be POSTing date times without timezones
    timezone.activate(util.setting("timezone", "UTC"))

    if duration:
        start = timezone.now()
        if duration.endswith("m"):
            end = start + datetime.timedelta(minutes=int(duration[:-1]))
        elif duration.endswith("h"):
            end = start + datetime.timedelta(hours=int(duration[:-1]))
        elif duration.endswith("d"):
            end = start + datetime.timedelta(days=int(duration[:-1]))
        else:
            raise ValidationError("Unknown time modifier")
        kwargs["startsAt"] = start.isoformat()
        kwargs["endsAt"] = end.isoformat()
    else:
        for key in ["startsAt", "endsAt"]:
            dt = parser.parse(kwargs[key])
            if timezone.is_naive(dt):
                dt = timezone.make_aware(dt)
            kwargs[key] = dt.isoformat()
    # If no matchers are provided, it means the method is called from ProxySilences (V1). In this
    # case, we need to convert labels to matchers.
    #
    # Otherwise, the method is called from ProxySilencesV2 and the matchers are already provided in
    # the right format, so we don't need to touch them.
    if "matchers" not in kwargs:
        kwargs["matchers"] = [
            {
                "name": name,
                "value": value,
                "isEqual": True,  # Only = and =~ are supported in ProxySilences (V1)
                "isRegex": True if value.endswith("*") else False,
            }
            for name, value in labels.items()
        ]

    logger.debug("Sending silence for %s", kwargs)
    url = urljoin(util.setting("alertmanager:url"), "/api/v2/silences")
    response = util.post(url, json=kwargs)
    response.raise_for_status()
    return response
