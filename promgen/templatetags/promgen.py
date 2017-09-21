# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import collections
import difflib
import json

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


@register.simple_tag
def qsfilter(request, k, v):
    '''
    Helper to rewrite query string for URLs

    {% qsfilter request 'foo' 'baz' %}
    When passed the request object, it will take a querystring like
    ?foo=bar&donottouch=1
    and change it to
    ?foo=baz&donottouch=1

    Useful when working with filtering on a page that also uses pagination to
    avoid losing other query strings
    {% qsfilter request 'page' page_obj.previous_page_number %}
    '''
    dict_ = request.GET.copy()
    if v:
        dict_[k] = v
    else:
        dict_.pop(k, None)
    return dict_.urlencode()


@register.simple_tag
def diff_json(a, b):
    if isinstance(a, str):
        a = json.loads(a)
    if isinstance(b, str):
        b = json.loads(b)
    a = json.dumps(a, indent=4, sort_keys=True).splitlines(keepends=True)
    b = json.dumps(b, indent=4, sort_keys=True).splitlines(keepends=True)
    diff = ''.join(difflib.unified_diff(a, b))
    if diff:
        return diff
    return 'No Changes'


@register.filter()
def pretty_json(data):
    if isinstance(data, str):
        data = json.loads(data)
    return json.dumps(data, indent=4, sort_keys=True)
