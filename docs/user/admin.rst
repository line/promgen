Administration Tasks
====================

Since Promgen is a standard `django <https://www.djangoproject.com/>`__ many tasks can be handled through `Django's admin <https://docs.djangoproject.com/en/1.11/ref/contrib/admin/>`__. or through management commands.

.. image:: /images/admin.png

Managing Shards using CLI
-------------------------

.. code-block:: bash

    # Register a Prometheus server running on the host prometheus002 on port 9090
    # to the shard 'promshard'
    promgen register promshard prometheus002 9090
