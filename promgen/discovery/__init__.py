# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE


FARM_DEFAULT = "promgen"


class DiscoveryBase:
    remote = True

    """
    Basic discovery plugin base

    Child classes should implement both fetch and farm methods
    """

    def fetch(self, farm):
        """
        Return list of hosts for farm
        """
        raise NotImplemented()

    def farms(self):
        """
        Return a list of farm names
        """
        raise NotImplemented()
