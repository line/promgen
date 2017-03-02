import requests

from promgen.version import __version__


def post(url, *args, **kwargs):
    '''Wraps requests.post with our user-agent'''
    if 'headers' not in kwargs:
        kwargs['headers'] = {}
    kwargs['headers']['user-agent'] = 'promgen/{}'.format(__version__)

    return requests.post(url, *args, **kwargs)


def get(url, *args, **kwargs):
    '''Wraps requests.post with our user-agent'''
    if 'headers' not in kwargs:
        kwargs['headers'] = {}
    kwargs['headers']['user-agent'] = 'promgen/{}'.format(__version__)

    return requests.get(url, *args, **kwargs)
