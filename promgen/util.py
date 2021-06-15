# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import argparse

import requests

from django.conf import settings
from django.db.models import F

from promgen.version import __version__

# Wrappers around request api to ensure we always attach our user agent
# https://github.com/requests/requests/blob/master/requests/api.py


USER_AGENT = "promgen/{}".format(__version__)
ACCEPT_HEADER = "application/openmetrics-text; version=0.0.1,text/plain;version=0.0.4;q=0.5,*/*;q=0.1"


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
    headers["X-Prometheus-Scrape-Timeout-Seconds"] = 10.0
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


# Comment wrappers to get the docstrings from the upstream functions
get.__doc__ = requests.get.__doc__
post.__doc__ = requests.post.__doc__
delete.__doc__ = requests.delete.__doc__
