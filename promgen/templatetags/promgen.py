# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

from django import template

register = template.Library()


@register.filter()
def to_prom(value):
    values = [
        '{}="{}"'.format(k, v) for k, v in value.items()
    ]

    return '{' + ', '.join(sorted(values)) + '}'
