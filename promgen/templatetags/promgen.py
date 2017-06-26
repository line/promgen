# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import collections

from django import template

register = template.Library()

EXCLUSION_MACRO = '<exclude>'


@register.filter()
def to_prom(value):
    values = [
        '{}="{}"'.format(k, v) for k, v in value.items()
    ]

    return '{' + ', '.join(sorted(values)) + '}'


@register.filter()
def rulemacro(value, rule):
    labels = collections.defaultdict(list)
    for r in rule.overrides.all():
        labels[r.content_type.model].append(r.content_object.name)

    filters = {
        k: '|'.join(labels[k]) for k in sorted(labels)
    }
    macro = ','.join(
        sorted('{}!~"{}"'.format(k, v) for k, v in filters.items())
    )
    return value.replace(EXCLUSION_MACRO, macro)
