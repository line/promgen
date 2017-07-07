# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

'''
Deduplicated remote events

Since many different actions can trigger a write of the target.json or rules
files, we need to handle some deduplication. This is handled by using the django
caching system to set a key and then triggering the actual event from middleware
'''

import logging
import re
from threading import local

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login

from promgen.signals import (trigger_write_config, trigger_write_rules,
                             trigger_write_urls)

logger = logging.getLogger(__name__)


UNAUTHENTICATED_WHITELIST = re.compile('^/(%s)' % '|'.join(
    re.escape(s) for s in [
        '__debug__',
        'alert',
        'api/v1',
        'complete',
        'login',
        'metrics',
    ]
))


_user = local()


class RemoteTriggerMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
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


class RequireLoginMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if UNAUTHENTICATED_WHITELIST.match(request.get_full_path()):
            logger.debug('Alowing unauthenticated for %s', request.get_full_path())
            return self.get_response(request)
        if request.user.is_authenticated():
            _user.value = request.user
            return self.get_response(request)

        logger.debug('Requires authentication for %s', request.get_full_path())
        return redirect_to_login(request.get_full_path())


def get_current_user():
    return getattr(_user, 'value', None)
