# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import logging

from django.shortcuts import get_object_or_404

from promgen import models
from promgen import discovery

logger = logging.getLogger(__name__)


class DiscoveryPromgen(discovery.DiscoveryBase):
    remote = False

    '''Promgen local database discovery plugin

    This is the default discovery plugin for farms and hosts stored locally in
    promgen's database. They are queried directly from Django's ORM
    '''

    def fetch(self, farm_name):
        '''Fetch list of hosts for a farm from the local database'''
        farm = get_object_or_404(models.Farm, name=farm_name)
        for host in models.Host.objects.filter(farm=farm):
            yield host.name

    def farms(self):
        '''Fetch farms from local database'''
        for farm in models.Farm.objects.filter(source=discovery.FARM_DEFAULT):
            yield farm.name
