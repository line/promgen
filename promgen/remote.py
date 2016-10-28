import logging

from django.shortcuts import get_object_or_404

from promgen import models

logger = logging.getLogger(__name__)


def fetch(farm_name):
    farm = get_object_or_404(models.Farm, name=farm_name)
    for host in models.Host.objects.filter(farm=farm):
        yield host.name


def farms():
    for farm in models.Farm.objects.filter(source=models.FARM_DEFAULT):
        yield farm.name
