# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

from urllib.parse import urlunsplit

from django.conf import settings
from django.shortcuts import resolve_url
from promgen import models


def resolve_domain(*args, **kwargs):
    return urlunsplit(
        (
            settings.PROMGEN_SCHEME,
            models.Site.objects.get_current().domain,
            resolve_url(*args, **kwargs),
            "",
            "",
        )
    )
