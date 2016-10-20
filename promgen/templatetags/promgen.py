from django import template
import json
register = template.Library()


@register.filter(name='json_to_prom')
def json_to_prom(value):
    value = json.loads(value)
    values = [
        '{}="{}"'.format(k, v) for k, v in value.iteritems()
    ]

    return '{' + ','.join(values) + '}'
