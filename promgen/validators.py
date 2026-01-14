# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import re

from dateutil import parser
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, URLValidator

# See definition of duration field
# https://prometheus.io/docs/prometheus/latest/configuration/configuration/#configuration-file

duration = RegexValidator(
    r"[0-9]+(ms|[smhdwy])",
    "Invalid or missing duration suffix. Example: 30s, 5m, 1h ([0-9]+(ms|[smhdwy])",
)

# Label Value Definition
# https://prometheus.io/docs/concepts/data_model/#metric-names-and-labels
metricname = RegexValidator(
    r"^[a-zA-Z_:][a-zA-Z0-9_:]*$",
    "Only alphanumeric characters are allowed.",
)
labelname = RegexValidator(
    r"^[a-zA-Z_][a-zA-Z0-9_]*$",
    "Only alphanumeric characters are allowed.",
)

# While Prometheus accepts label values of any unicode character, our values sometimes
# make it into URLs, so we want to make sure we do not have stray / characters
labelvalue = RegexValidator(
    r"^[\w][- \w]+$", "Unicode letters, numbers, underscores, or hyphens or spaces"
)

hostname = RegexValidator(
    regex=r"^("
    + URLValidator.ipv4_re
    + "|"
    + URLValidator.ipv6_re
    + "|"
    + URLValidator.host_re
    + "|"
    + URLValidator.hostname_re
    + ")$",
    message="Invalid hostname: %(value)s",
    flags=re.IGNORECASE,
)

# The default URLValidator would consider following schemas valid: ['http', 'https', 'ftp', 'ftps'].
# However, we only want to allow http and https URLs to be scraped, since Prometheus cannot directly
# scrape ftp target.
scraped_url = URLValidator(
    schemes=["http", "https"],
)


def datetime(value):
    try:
        parser.parse(value)
    except ValueError:
        raise ValidationError("Invalid timestamp")
