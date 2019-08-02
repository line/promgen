# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

from urllib.parse import urlunsplit

from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.shortcuts import resolve_url


def resolve_domain(*args, **kwargs):
    return urlunsplit(
        (
            settings.PROMGEN_SCHEME,
            get_current_site(None).domain,
            resolve_url(*args, **kwargs),
            "",
            "",
        )
    )
