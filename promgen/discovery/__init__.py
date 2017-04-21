# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE


class DiscoveryBase(object):
    def fetch(self, farm):
        raise NotImplemented()

    def farms(self):
        raise NotImplemented()
