API
***

Prometheus Proxy API
====================

Promgen provides a simple proxy api to proxy certain requests across all managed
Prometheus nodes. See the `Prometheus API <https://prometheus.io/docs/prometheus/latest/querying/api/>`__ for more details


.. http:get:: /api/v1/label/(string:labelname)/values

.. http:get:: /api/v1/series

.. http:get:: /api/v1/query_range


Promgen API
===========

.. http:get:: /api/v1/alerts

.. http:get:: /api/v1/targets

.. http:get:: /api/v1/rules

.. http:get:: /api/v1/urls

.. http:get:: /api/v1/host/(string:hostname)
