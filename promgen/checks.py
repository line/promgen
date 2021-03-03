import os
import pathlib

from django.conf import settings
from django.core import checks

from promgen import util


@checks.register("settings")
def directories(**kwargs):
    for key in ["prometheus:rules", "prometheus:blackbox", "prometheus:targets"]:
        try:
            path = pathlib.Path(util.setting(key)).parent
        except TypeError:
            yield checks.Warning(
                "Missing setting for %s in %s " % (key, settings.PROMGEN_CONFIG_FILE),
                id="promgen.W001",
            )
        else:
            if not os.access(path, os.W_OK):
                yield checks.Warning("Unable to write to %s" % path, id="promgen.W002")


@checks.register("settings")
def promtool(**kwargs):
    key = "prometheus:promtool"
    try:
        path = pathlib.Path(util.setting(key))
    except TypeError:
        yield checks.Warning(
            "Missing setting for %s in %s " % (key, settings.PROMGEN_CONFIG_FILE),
            id="promgen.W001",
        )
    else:
        if not os.access(path, os.X_OK):
            yield checks.Warning("Unable to execute file %s" % path, id="promgen.W003")
