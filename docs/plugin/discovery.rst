Writing Discovery Plugins
=========================

Promgen uses discovery plugins to bridge non-natively supported discovery
mechanisms to Prometheus's file configuration format. They should be registered
using setuptools entry_points_.

.. code-block:: python

    entry_points={
        'promgen.discovery': [
            'example = module.path.discovery:DiscoveryExample',
        ],
    }


Plugins should inherit from DiscoveryBase, should implement *farms()* and
*fetch()* methods

.. code-block:: python

    from promgen.discovery import DiscoveryBase

    EXAMPLE = {
      'Farm-A': ['AA', 'AB', 'AC']
      'Farm-B': ['BA', 'BB', 'BC', 'BD']
    }

    class DiscoveryExample(DiscoveryBase):
      def fetch(self, farm_name):
          return EXAMPLE[farm_name]

      def farms(self):
          return EXAMPLE.keys()



.. _entry_points: http://setuptools.readthedocs.io/en/latest/setuptools.html#automatic-script-creation
