# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from dateutil import parser

alphanumeric = RegexValidator(r'^[0-9a-zA-Z_]*$', 'Only alphanumeric characters are allowed.')


# See definition of duration field
# https://prometheus.io/docs/prometheus/latest/configuration/configuration/#configuration-file

duration = RegexValidator(
    r"[0-9]+(ms|[smhdwy])",
    "Invalid or missing duration suffix. Example: 30s, 5m, 1h ([0-9]+(ms|[smhdwy])",
)


def datetime(value):
    try:
        parser.parse(value)
    except ValueError:
        raise ValidationError("Invalid timestamp")
