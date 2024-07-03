# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import argparse
from urllib.parse import urlsplit

import requests
from django.conf import settings
from django.db.models import F
from django.http import HttpResponse

# Wrappers around request api to ensure we always attach our user agent
# https://github.com/requests/requests/blob/master/requests/api.py


USER_AGENT = f"promgen/{settings.PROMGEN_VERSION}"
ACCEPT_HEADER = (
    "application/openmetrics-text; version=0.0.1,text/plain;version=0.0.4;q=0.5,*/*;q=0.1"
)


def post(url, data=None, json=None, **kwargs):
    headers = kwargs.setdefault("headers", {})
    headers["User-Agent"] = USER_AGENT
    return requests.post(url, data=data, json=json, **kwargs)


def get(url, params=None, **kwargs):
    headers = kwargs.setdefault("headers", {})
    headers["User-Agent"] = USER_AGENT
    return requests.get(url, params=params, **kwargs)


def delete(url, **kwargs):
    headers = kwargs.setdefault("headers", {})
    headers["User-Agent"] = USER_AGENT
    return requests.delete(url, **kwargs)


def scrape(url, params=None, **kwargs):
    """
    Scrape Prometheus target

    Light wrapper around requests.get so that we add required
    Accept headers that a target might expect
    """
    headers = kwargs.setdefault("headers", {})
    headers["Accept"] = ACCEPT_HEADER
    headers["User-Agent"] = USER_AGENT
    headers["X-Prometheus-Scrape-Timeout-Seconds"] = "10.0"
    # According to the spec, having the host with a port is optional, though
    # so by default, many clients/servers drop the port if it's known (http/https)
    # in the case of Prometheus it always forces the port in the Host header which
    # then sometimes fail for servers that do not expect it. Here we force the port
    # in the Host header to make it match how Prometheus scrapes
    # https://github.com/prometheus/prometheus/blob/2b55017379786873dc00315ffe65e22ad7026abb/scrape/target.go#L375-L387
    headers["Host"] = urlsplit(url).netloc
    return requests.get(url, params=params, **kwargs)


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
    lookup = key.split(":")

    if domain:
        lookup.insert(0, domain)

    for index in lookup:
        try:
            rtn = rtn[index]
        except KeyError:
            if default != KeyError:
                return default
            raise KeyError(f"Missing required setting: {key}")
    return rtn


def inc_for_pk(model, pk, **kwargs):
    # key=F('key') + value
    model.objects.filter(pk=pk).update(**{key: F(key) + kwargs[key] for key in kwargs})


def cast(klass):
    """
    Used with argparse to cast to a Django model

    Example:
    parser.add_argument("project", type=util.cast(models.Project))
    """

    def wrapped(value):
        try:
            return klass.objects.get(name=value)
        except klass.DoesNotExist:
            raise argparse.ArgumentTypeError("Unable to find :%s" % value)

    return wrapped


def help_text(klass):
    """
    Used with argparse to lookup help_text for a Django model

    Example:
    help_text = util.help_text(models.Host)
    parser.add_argument("host", help=help_text("name"))
    """

    def wrapped(field):
        return klass._meta.get_field(field).help_text

    return wrapped

def proxy_error(response: requests.Response) -> HttpResponse:
    """
    Return a wrapped proxy error

    Taking a request.response object as input, return it slightly modified
    with an extra header for debugging so that we can see where the request
    failed
    """
    r = HttpResponse(
        response.content,
        content_type=response.headers["content-type"],
        status=response.status_code,
    )
    r.setdefault("X-PROMGEN-PROXY", response.url)
    return r


# Comment wrappers to get the docstrings from the upstream functions
get.__doc__ = requests.get.__doc__
post.__doc__ = requests.post.__doc__
delete.__doc__ = requests.delete.__doc__
