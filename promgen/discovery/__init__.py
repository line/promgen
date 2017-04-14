class DiscoveryBase(object):
    def fetch(self, farm):
        raise NotImplemented()

    def farms(self):
        raise NotImplemented()
