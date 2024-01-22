# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import logging
import textwrap

from django import forms
from django.template.loader import render_to_string

from promgen import models, plugins, util

logger = logging.getLogger(__name__)


def load(name):
    for driver in plugins.notifications():
        if name == driver.module_name:
            return driver.load()()
    raise ImportError("Unknown notification plugin %s" % name)


class FormSenderBase(forms.Form):
    value = forms.CharField(required=True)
    alias = forms.CharField(required=False)


class NotificationBase:
    """
    Base Notification class
    """

    form = FormSenderBase

    @classmethod
    def create(cls, **kwargs) -> models.Sender:
        return models.Sender.objects.create(sender=cls.__module__, **kwargs)

    @classmethod
    def help(cls):
        if cls.__doc__:
            return textwrap.dedent(cls.__doc__)

    def _send(self, target, alert):
        """
        Sender specific implementation

        This function will receive some kind of target value, such as an email
        address or post endpoint and an individual alert combined with some
        additional alert meta data
        """
        raise NotImplementedError()

    def config(self, key, default=KeyError):
        """
        Plugin specific configuration

        This wraps our PROMGEN settings so that a plugin author does not need to
        be concerned with how the configuration files are handled but only about
        the specific key.
        """
        try:
            return util.setting(key, default=default, domain=self.__module__)
        except KeyError as e:
            raise KeyError(f"Missing key for domain: {self.__module__} {key}") from e

    def render(self, template, context):
        s = render_to_string(template, context).strip()
        # Uncomment to re-generate test templates
        # with open(template.replace('sender', 'tests/notification'), 'w+') as fp:
        #     fp.write(s)
        return s
