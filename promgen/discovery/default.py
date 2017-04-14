import logging

from django.shortcuts import get_object_or_404

from promgen import models
from promgen.discovery import DiscoveryBase

logger = logging.getLogger(__name__)


class DiscoveryPromgen(DiscoveryBase):
    def fetch(self, farm_name):
        farm = get_object_or_404(models.Farm, name=farm_name)
        for host in models.Host.objects.filter(farm=farm):
            yield host.name

    def farms(self):
        for farm in models.Farm.objects.filter(source=models.FARM_DEFAULT):
            yield farm.name
