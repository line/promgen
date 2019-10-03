# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

from promgen import models, util
from promgen.version import __version__


def settings_in_view(request):
    return {
        "EXTERNAL_LINKS": util.setting("links", {}),
        "TIMEZONE": util.setting("timezone", "UTC"),
        "VERSION": __version__,
        "DEFAULT_EXPORTERS": models.DefaultExporter.objects.order_by("job", "-port"),
    }
