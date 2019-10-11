# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import requests.sessions

from promgen.version import __version__

from django.conf import settings

# Wrappers around request api to ensure we always attach our user agent
# https://github.com/requests/requests/blob/master/requests/api.py


def post(url, data=None, json=None, **kwargs):
    with requests.sessions.Session() as session:
        session.headers['User-Agent'] = 'promgen/{}'.format(__version__)
        return session.post(url, data=data, json=json, **kwargs)


def get(url, params=None, **kwargs):
    with requests.sessions.Session() as session:
        session.headers['User-Agent'] = 'promgen/{}'.format(__version__)
        return session.get(url, params=params, **kwargs)


def delete(url, **kwargs):
    with requests.sessions.Session() as session:
        session.headers['User-Agent'] = 'promgen/{}'.format(__version__)
        return session.delete(url, **kwargs)


def setting(key, default=None, domain=None):
    """
    Settings helper based on saltstack's query

    Allows a simple way to query settings from YAML
    using the style `path:to:key` to represent
    
    path:
      to:
        key: value
    """
    rtn = settings.PROMGEN
    if domain:
        rtn = rtn[domain]
    for index in key.split(":"):
        try:
            rtn = rtn[index]
        except KeyError:
            return default
    return rtn
