# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

from dateutil import parser

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, validate_unicode_slug

# See definition of duration field
# https://prometheus.io/docs/prometheus/latest/configuration/configuration/#configuration-file

duration = RegexValidator(
    r"[0-9]+(ms|[smhdwy])",
    "Invalid or missing duration suffix. Example: 30s, 5m, 1h ([0-9]+(ms|[smhdwy])",
)

# Label Value Definition
# https://prometheus.io/docs/concepts/data_model/#metric-names-and-labels
metricname = RegexValidator(
    r"[a-zA-Z_:][a-zA-Z0-9_:]*", "Only alphanumeric characters are allowed."
)
labelname = RegexValidator(
    r"[a-zA-Z_][a-zA-Z0-9_]*", "Only alphanumeric characters are allowed."
)
labelvalue = validate_unicode_slug


def datetime(value):
    try:
        parser.parse(value)
    except ValueError:
        raise ValidationError("Invalid timestamp")
