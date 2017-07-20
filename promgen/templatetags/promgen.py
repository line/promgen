# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import collections

from django import template

register = template.Library()

EXCLUSION_MACRO = '<exclude>'


@register.filter()
def to_prom(value):
    '''
    Render a Python dictionary using Prometheus' dictonary format
    '''
    values = [
        '{}="{}"'.format(k, v) for k, v in value.items()
    ]

    return '{' + ', '.join(sorted(values)) + '}'


@register.filter()
def rulemacro(value, rule):
    '''
    Macro rule expansion

    Assuming a list of rules with children and parents, expand our macro to exclude child rules

    .. code-block:: none

        foo{<exclude>} / bar{<exclude>} > 5 # Parent Rule
        foo{project="A", <exclude>} / bar{project="A", <exclude>} > 3 # Child Rule
        foo{project="B"} / bar{project="B"} > 4 # Child Rule

        foo{project~="A|B"} / bar{project~="A|B"} > 5
        foo{project="A", } / bar{project="A"} > 3
        foo{project="B"} / bar{project="B"} > 4
    '''

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
