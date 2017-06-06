# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import requests.sessions

from promgen.version import __version__


def post(url, *args, **kwargs):
    with requests.sessions.Session() as session:
        session.headers['User-Agent'] = 'promgen/{}'.format(__version__)
        return session.post(url, *args, **kwargs)


def get(url, *args, **kwargs):
    with requests.sessions.Session() as session:
        session.headers['User-Agent'] = 'promgen/{}'.format(__version__)
        return session.get(url, *args, **kwargs)


def delete(url, *args, **kwargs):
    with requests.sessions.Session() as session:
        session.headers['User-Agent'] = 'promgen/{}'.format(__version__)
        return session.delete(url, *args, **kwargs)
