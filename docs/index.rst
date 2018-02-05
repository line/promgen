.. Promgen documentation master file, created by
   sphinx-quickstart on Mon Mar 27 15:39:54 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Promgen's documentation!
===================================

.. toctree::
  :maxdepth: 2
  :hidden:

  worker
  rules
  docker
  django-conf
  terms

.. toctree::
  :hidden:

  plugin/auth
  plugin/discovery
  plugin/notification


.. image:: images/screenshot.png


Overview
--------

.. image:: images/overview.png

1. Promgen manages a list of Targets and Rules that it deploys to a Prometheus server
2. Prometheus will load these settings and proceed to scrape targets
3. When an alert fires, it will be sent to AlertManager
4. AlertManager will group on labels and handle de-duplication and forward to Promgen
5. Promgen will route the message based on labels to the correct notification
