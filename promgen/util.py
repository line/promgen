# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import requests.sessions

from promgen.version import __version__

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
