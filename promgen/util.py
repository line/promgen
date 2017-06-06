# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import requests.sessions

from promgen.version import __version__


def post(url, **kwargs):
    with requests.sessions.Session() as session:
        session.headers['User-Agent'] = 'promgen/{}'.format(__version__)
        return session.post(url, **kwargs)


def get(url, **kwargs):
    with requests.sessions.Session() as session:
        session.headers['User-Agent'] = 'promgen/{}'.format(__version__)
        return session.get(url, **kwargs)

def delete(url, **kwargs):
    with requests.sessions.Session() as session:
        session.headers['User-Agent'] = 'promgen/{}'.format(__version__)
        return session.delete(url, **kwargs)
