# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import logging
import textwrap

from django import forms
from django.template.loader import render_to_string

from promgen import plugins, util

logger = logging.getLogger(__name__)


def load(name):
    for driver in plugins.notifications():
        if name == driver.module_name:
            return driver.load()()
    raise ImportError("Unknown notification plugin %s" % name)


class FormSenderBase(forms.Form):
    value = forms.CharField(required=True)
    alias = forms.CharField(required=False)


class NotificationBase(object):
    '''
    Base Notification class
    '''

    form = FormSenderBase

    @classmethod
    def help(cls):
        if cls.__doc__:
            return textwrap.dedent(cls.__doc__)

    def _send(self, target, alert):
        '''
        Sender specific implmentation

        This function will receive some kind of target value, such as an email
        address or post endpoint and an individual alert combined with some
        additional alert meta data
        '''
        raise NotImplementedError()

    def config(self, key):
        '''
        Plugin specific configuration

        This wraps our PROMGEN settings so that a plugin author does not need to
        be concerned with how the configuration files are handled but only about
        the specific key.
        '''
        try:
            return util.setting(key, domain=self.__module__)
        except KeyError:
            logger.error('Undefined setting. Please check for %s under %s in settings.yml', key, self.__module__)

    def render(self, template, context):
        s = render_to_string(template, context).strip()
        # Uncomment to re-generate test templates
        # with open(template.replace('sender', 'tests/notification'), 'w+') as fp:
        #     fp.write(s)
        return s
