Distributed task queues
=======================

Promgen uses Celery as a distributed system to handle asynchronous tasks such as sending alert
notifications (see: :ref:`alert_worker`) or pushing updates to Prometheus (see: :ref:`worker_model`).

.. image:: /images/task_queues.png

Tasks are sent to workers using Redis as the message broker. Tasks that relate to a specific
Prometheus server, such as writing configuration files and reloading Prometheus, are sent to a queue
named after that server. Other tasks, such as sending alert notifications, are sent to a default
queue named "celery".

Retrying Timed Out Tasks
-------------------------

Tasks that process for too long are automatically retried after a timeout period to avoid
stuck tasks. The timeout period is currently set to 30 seconds, but this can be adjusted
by modifying the `CELERY_TASK_SOFT_TIME_LIMIT` setting in the Promgen configuration.

Tasks that time out will be retried indefinitely until they succeed. This ensures that
important tasks, such as sending alert notifications, are not lost due to temporary issues.
The delay between retries increases exponentially to avoid overwhelming the system.
