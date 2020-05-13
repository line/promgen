import os
import pathlib

from django.conf import settings
from django.core import checks

from promgen import models, util


@checks.register(checks.Tags.models)
def sites(app_configs, **kwargs):
    if models.Site.objects.count() == 0:
        yield checks.Error(
            "Site not configured", hint="Missing django site configuration"
        )

    for site in models.Site.objects.filter(
        pk=settings.SITE_ID, domain__in=["example.com"]
    ):
        yield checks.Error(
            "Site not configured", obj=site, hint="Please update from admin panel"
        )


@checks.register(checks.Tags.models)
def shards(**kwargs):
    if models.Shard.objects.filter(enabled=True).count() == 0:
        yield checks.Warning("Missing shards", hint="Ensure some shards are enabled")
    if models.Shard.objects.filter(proxy=True).count() == 0:
        yield checks.Warning("No proxy shards", hint="Ensure some shards are enabled")


@checks.register("settings")
def directories(**kwargs):
    for key in ["prometheus:rules", "prometheus:blackbox", "prometheus:targets"]:
        try:
            path = pathlib.Path(util.setting(key)).parent
        except TypeError:
            yield checks.Warning(
                "Missing setting for %s in %s " % (key, settings.PROMGEN_CONFIG_FILE)
            )
        else:
            if not os.access(path, os.W_OK):
                yield checks.Warning("Unable to write to %s" % path)


@checks.register("settings")
def promtool(**kwargs):
    key = "prometheus:promtool"
    try:
        path = pathlib.Path(util.setting(key))
    except TypeError:
        yield checks.Warning(
            "Missing setting for %s in %s " % (key, settings.PROMGEN_CONFIG_FILE)
        )
    else:
        if not os.access(path, os.X_OK):
            yield checks.Warning("Unable to execute file %s" % path)
