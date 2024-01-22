Glossary
========

.. graphviz::

    digraph {
      rankdir=RL;
      { Rule Notifier Project} -> Service;
      { Project Prometheus} -> Shard;
      { Rule Notifier Exporter URL Farm} -> Project;
      Host -> Farm;
      { rank=same Notifier Rule };
   }


Shard
-----

Shards are a collection of Prometheus servers monitoring the same targets.

Service
-------

A service in Promgen is a group of related Projects and Rules.
Service is typically the top-level object in Promgen.

Projects
--------
Projects are one of the main groupings for Promgen. This represents a typical
monitoring target and brings together a collection of servers (Farm) with
Exporters and URL endpoints. They are assigned to a Shard.

Farm
----
Farm is a group of servers. Farms may be updated using :doc:`discovery plugins </plugin/discovery>`.

Notifiers
---------
:doc:`Notifiers </plugin/notification>` are used for routing messages to a specific destination such as Email or
LINE Notify.
They can be assigned to either a Project or a Service, watching for alerts that match that label.

Rule
----
Rules represent the rules that Prometheus itself uses for alerting.
They can be assigned to a Project, or assigned to a parent Service that covers multiple Projects.

Exporter
--------

These correspond to `Prometheus exporters`_ and other monitoring integrations.

URL
---

These are URLs that are monitored via `blackbox_exporter`_

.. _Prometheus exporters:  https://prometheus.io/docs/instrumenting/exporters/
.. _blackbox_exporter:  https://github.com/prometheus/blackbox_exporter
