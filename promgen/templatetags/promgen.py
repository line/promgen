from django import template

register = template.Library()


@register.filter()
def to_prom(value):
    values = [
        '{}="{}"'.format(k, v) for k, v in value.items()
    ]

    return '{' + ', '.join(sorted(values)) + '}'
