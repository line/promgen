# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

from django.conf import settings

from promgen import models, util


def settings_in_view(request):
    return {
        "TIMEZONE": util.setting("timezone", "UTC"),
        "VERSION": settings.PROMGEN_VERSION,
        "DEFAULT_EXPORTERS": models.DefaultExporter.objects.order_by("job", "-port"),
    }
