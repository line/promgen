.. _alert_worker:

Alert Worker
============

Alerts that are routed through Promgen are added to a celery queue to be processed

Running under systemd
---------------------

.. code-block:: none

  [Unit]
  Description=Promgen Worker
  After=network.target

  [Service]
  Type=simple
  ExecStart=/path/to/virtualenv/bin/celery -A promgen worker -l info
  Restart=on-failure
  User=edge-dev

  [Install]
  WantedBy=multi-user.target
