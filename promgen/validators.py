# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

alphanumeric = RegexValidator(r'^[0-9a-zA-Z_]*$', 'Only alphanumeric characters are allowed.')


def prometheusduration(value):
    # See valid range selectors in Prometheus docs
    # https://prometheus.io/docs/querying/basics/#range-vector-selectors
    if value.lower()[-1:] not in 'smhdwy':
        raise ValidationError('Invalid or missing duration suffix. Example: 30s, 5m, 1h')
    try:
        int(value[:-1])
    except:
        raise ValidationError("Invalid duraiton. Example: 30s, 5m, 1h")
