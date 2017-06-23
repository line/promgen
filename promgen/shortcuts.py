# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

from django.contrib.sites.shortcuts import get_current_site
from django.shortcuts import resolve_url


def resolve_domain(*args, **kwargs):
    return 'http://{site}{path}'.format(
        site=get_current_site(None),
        path=resolve_url(*args, **kwargs)
    )
