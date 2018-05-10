# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

'''
Promgen middleware

The middleware ensures three main things

1. We globally set request.site so that we can easily use it when searching for
   our global rule_set object

2. We store request.user globally so that we can retrieve it when logging users
   to our AuditLog

3. Since many different actions can trigger a write of the target.json or rules
files, we need to handle some deduplication. This is handled by using the django
caching system to set a key and then triggering the actual event from middleware
'''

import logging
from threading import local

from django.contrib import messages
from django.db.models import prefetch_related_objects

from promgen import models
from promgen.signals import (trigger_write_config, trigger_write_rules,
                             trigger_write_urls)

logger = logging.getLogger(__name__)


_user = local()


class PromgenMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # This works the same as the django middleware
        # django.contrib.sites.middleware.CurrentSiteMiddleware
        # but ensures that it uses our proxy object so that test cases
        # properly find our rule_set object
        request.site = models.Site.objects.get_current()
        # Prefetch our rule_set as needed, since request.site is used on
        # many different pages
        prefetch_related_objects([request.site], 'rule_set')

        # Get our logged in user to use with our audit logging plugin
        if request.user.is_authenticated:
            _user.value = request.user

        response = self.get_response(request)

        triggers = {
            'Config': trigger_write_config.send,
            'Rules': trigger_write_rules.send,
            'URLs': trigger_write_urls.send,
        }

        for msg, func in triggers.items():
            for (receiver, status) in func(self, request=request, force=True):
                if status is False:
                    messages.warning(request, 'Error queueing %s ' % msg)
        return response


def get_current_user():
    return getattr(_user, 'value', None)
