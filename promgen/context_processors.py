# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

from django.conf import settings
from promgen import models
from promgen.version import __version__


def settings_in_view(request):
    return {
        'EXTERNAL_LINKS': settings.PROMGEN.get('links', {}),
        'TIMEZONE': settings.PROMGEN.get('timezone', 'UTC'),
        'VERSION': __version__,
        'DEFAULT_EXPORTERS': models.DefaultExporter.objects.order_by('job', '-port'),
    }
