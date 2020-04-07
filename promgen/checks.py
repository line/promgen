from django.conf import settings
from django.core import checks

from promgen import models


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
        yield checks.Warning("Missing shards", hint="Ensure some shards are registerd")
    if models.Shard.objects.filter(proxy=True).count() == 0:
        yield checks.Warning("No proxy shards", hint="Ensure some shards are registerd")
