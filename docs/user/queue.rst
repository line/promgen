Distributed task queues
=======================

Promgen uses Celery as a distributed system to handle asynchronous tasks such as sending alert
notifications (see: :ref:`alert_worker`) or pushing updates to Prometheus (see: :ref:`worker_model`).

.. image:: /images/task_queues.png

Tasks are sent to workers using Redis as the message broker. Tasks that relate to a specific
Prometheus server, such as writing configuration files and reloading Prometheus, are sent to a queue
named after that server. Other tasks, such as sending alert notifications, are sent to a default
queue named "celery".
