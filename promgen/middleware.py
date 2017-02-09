'''
Deduplicated remote events

Since many different actions can trigger a write of the target.json or rules
files, we need to handle some deduplication. This is handled by using the django
caching system to set a key and then triggering the actual event from middleware
'''

from django.contrib import messages

from promgen.signals import trigger_write_config, trigger_write_rules, trigger_write_urls


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
            for (receiver, status) in func(self, force=True):
                if status is True:
                    messages.info(request, 'Triggered %s write ' % msg)
                elif status is False:
                    messages.warning(request, 'Error queueing %s ' % msg)
        return response
