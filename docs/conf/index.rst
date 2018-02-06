Installing Promgen
==================

.. toctree::
  :maxdepth: 2

  /conf/web
  /conf/prometheus
  /conf/alert
  /conf/docker
  /conf/django


.. image:: /images/overview.png

1. Promgen manages a list of Targets and Rules that it deploys to a Prometheus server
2. Prometheus will load these settings and proceed to scrape targets
3. When an alert fires, it will be sent to AlertManager
4. AlertManager will group on labels and handle de-duplication and forward to Promgen
5. Promgen will route the message based on labels to the correct notification
