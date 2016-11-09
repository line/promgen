import json

from django import template
from django.contrib.sites.models import Site
from django.urls import reverse

register = template.Library()


@register.filter()
def to_prom(value):
    value = json.loads(value)
    values = [
        '{}="{}"'.format(k, v) for k, v in value.items()
    ]

    return '{' + ', '.join(sorted(values)) + '}'


@register.filter()
def tag_service(value, service):
    data = json.loads(value)
    data['service'] = service.name
    return json.dumps(data)


@register.filter()
def service_url(value, service):
    data = json.loads(value)
    data['service'] = 'http://{site}{path}'.format(
        site=Site.objects.get_current().domain,
        path=reverse('service-detail', args=[service.id])
    )

    return json.dumps(data)
