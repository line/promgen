'''
Deduplicated remote events

Since many different actions can trigger a write of the target.json or rules
files, we need to handle some deduplication. This is handled by using the django
caching system to set a key and then triggering the actual event from middleware
'''

from django.contrib import messages
from django.core.cache import cache

from promgen.signals import write_config, write_rules


class RemoteTriggerMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if cache.get('write_config'):
            write_config.send(self)
            messages.info(request, 'Wrote Config')
            cache.delete('write_config')

        if cache.get('write_rules'):
            write_rules.send(self)
            messages.info(request, 'Wrote Rules')
            cache.delete('write_rules')

        return response
