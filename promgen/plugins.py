import logging

from django.shortcuts import get_object_or_404
from pkg_resources import working_set

from promgen import models

logger = logging.getLogger(__name__)


def remotes():
    return working_set.iter_entry_points('promgen.server')


def senders():
    return working_set.iter_entry_points('promgen.sender')


def fetch(farm_name):
    farm = get_object_or_404(models.Farm, name=farm_name)
    for host in models.Host.objects.filter(farm=farm):
        yield host.name


def farms():
    for farm in models.Farm.objects.filter(source=models.FARM_DEFAULT):
        yield farm.name
