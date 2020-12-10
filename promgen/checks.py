import os
import pathlib

from django.conf import settings
from django.core import checks

from promgen import models, util
from django.db.transaction import get_autocommit

# For a few of our checks, we want to be able to check the
# database for values that exist or not. The easiest? way
# to do this, seems to be to wrap our check with a check
# to the database to see if it is connected
def db_check(*tags):
    def outer(func):
        def inner(**kwargs):
            try:
                get_autocommit()
            except:
                yield checks.Warning(
                    "Database not reachable",
                    hint="Try running bootstrap again",
                    id="promgen.W000",
                )
            else:
                yield from func(**kwargs)

        return checks.register(check=inner, tags=tags)

    return outer


@db_check("promgen")
def sites(app_configs, **kwargs):
    if models.Site.objects.count() == 0:
        yield checks.Warning(
            "Site not configured",
            hint="Missing django site configuration",
            id="promgen.W006",
        )

    for site in models.Site.objects.filter(
        pk=settings.SITE_ID, domain__in=["example.com"]
    ):
        yield checks.Warning(
            "Promgen is configured to example domain",
            obj=site,
            hint="Please update from admin page /admin/",
            id="promgen.W007",
        )


@db_check("promgen")
def shards(**kwargs):
    if models.Shard.objects.filter(enabled=True).count() == 0:
        yield checks.Warning(
            "Missing shards", hint="Ensure some shards are enabled", id="promgen.W004"
        )
    if models.Shard.objects.filter(proxy=True).count() == 0:
        yield checks.Warning(
            "No proxy shards", hint="Ensure some shards are enabled", id="promgen.W004"
        )


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
