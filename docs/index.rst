.. Promgen documentation master file, created by
   sphinx-quickstart on Mon Mar 27 15:39:54 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Promgen's documentation!
===================================

.. toctree::
   :maxdepth: 2
   :hidden:

   terms
   docker

   plugin/notification
   plugin/discovery

   modules/models
   modules/notification
   modules/prometheus


.. image:: images/screenshot.png


.. graphviz::

  digraph G {
    Prometheus -> Exporters [color=blue, label="(2) Scrapes targets"]

    subgraph cluster {
      style = rounded;
      Prometheus -> AlertManager [color=red, label="(3) Generates Alerts"]
      AlertManager -> Promgen [color=red, label="(4) Forwards Alerts"]
      Promgen -> Prometheus [color=orange, label="(1) Generates Target and Rules"]
    }

    subgraph senders {
      style = rounded;
      Promgen -> Email
      Promgen -> Ikasan;
      Promgen -> LINENotify
      Promgen -> Webhook [label="(5) Routes to target based on labels"];
    }
  }
