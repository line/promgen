# Copyright (c) 2019 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import yaml
from rest_framework import renderers

from promgen import models, serializers


# https://www.django-rest-framework.org/api-guide/renderers/#custom-renderers
# https://prometheus.io/docs/prometheus/latest/configuration/recording_rules/#recording-rules
class RuleRenderer(renderers.BaseRenderer):
    format = "yaml"
    media_type = "application/x-yaml"
    charset = "utf-8"

    def render(self, data, media_type=None, renderer_context=None):
        return yaml.safe_dump(
            {"groups": [{"name": name, "rules": data[name]} for name in data]},
            default_flow_style=False,
            allow_unicode=True,
            encoding=self.charset,
        )


# https://prometheus.io/docs/prometheus/latest/configuration/configuration/#file_sd_config
class ScrapeRenderer(renderers.JSONRenderer):
    pass
    # TODO handle grouping


def rules(rules=None):
    if rules is None:
        rules = models.Rule.objects
    return RuleRenderer().render(
        serializers.AlertRuleSerializer(rules, many=True).data
    )


def urls():
    return ScrapeRenderer().render(
        serializers.UrlSeralizer(models.URL.objects, many=True).data
    )


def targets():
    return ScrapeRenderer().render(
        serializers.TargetSeralizer(models.Exporters.objects, many=True).data
    )
