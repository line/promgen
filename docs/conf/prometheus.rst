Prometheus Server
=================

One of Promgen's primary roles is to manage a list of targets for Prometheus to scrape.
For high availability, it is generally preferred to have multiple Prometheus servers running together.
There are multiple ways to deploy these targets to a Prometheus server.

Worker Model (Push)
-------------------

.. image:: /images/worker.png

Promgen's Push mode relies on `celery <http://docs.celeryproject.org>`__ to push updates to Prometheus.
A Promgen worker is run on each Prometheus server which subscribes to a named queue to signal when to write
out an updated configuration file, and update Prometheus.
Communication between Promgen and workers happens in Celery which in turn delegates this to the underlying broker mechanism: for example if you're using RabbitMQ as a broker then a change in the config in Promgen will send a message to the queue in RabbitMQ, a worker running on one of the many Prometheus servers will pick up that message which will tell it to update the `prometheus.yml` config in the local filesystem (it's assumed that this worker shares at least part of the filesystem with the Prometheus that it tries to update).

.. code-block:: bash

    # Assuming we have a Prometheus shard named promshard and two servers, we
    # may register the workers like this on the Promgen server (master)
    promgen register-server promshard prometheus001 9090
    promgen register-server promshard prometheus002 9090

    # Then on each Prometheus server, we would want to run a celery worker with
    # the queue name matching the name that we registered
    # Note that rabbitmq:5672 is the same RabbitMQ instance that Promgen has access to
    CELERY_BROKER_URL=amqp://rabbitmq:5672/ celery worker -A promgen -l info --queues prometheus001
    # If running within docker, the same command would look like this
    docker run --rm \
        -v ~/.config/promgen:/etc/promgen/ \
        -v /etc/prometheus:/etc/prometheus \
        line/promgen worker -l info --queues prometheus001


Cron Model (Pull)
-----------------

.. image:: /images/cron.png

In some cases it is not possible (or not desired) to install Promgen beside Prometheus.
In this case, Promgne's pull mode can be used by trigging a small script running from cron
or any other job framework. This only requires the server where Prometheus is running,
to be able to access Promgen over HTTP.

.. code-block:: bash

    #!/bin/sh
    set -e
    # Download all the targets from Promgen to a temporary file
    curl http://promgen/api/v1/targets --output /etc/prometheus/targets.tmp
    # Optionally you could download from a specific service or project
    # curl http://promgen/service/123/targets -o /etc/prometheus/targets.tmp
    # curl http://promgen/project/456/targets -o /etc/prometheus/targets.tmp
    # Move our file to make it more atomic
    mv /etc/prometheus/targets.tmp /etc/prometheus/targets.json
    # Tell Prometheus to reload
    curl -XPOST http://localhost:9090/-/reload


If it's possible to install Promgen, then there is a Promgen helper command that
handles the same basic steps as the above command. This will however require
the Prometheus server to be able to access the same database as the Promgen
web instance.

.. code-block:: bash

    # Internally Promgen uses an atomic write function so you can give
    # it the path where you want to save it and have it --reload automatically
    promgen targets /etc/prometheus/targets.json --reload


Filtering Targets (Both)
------------------------

In both models, you will want to ensure that the Prometheus server only scrapes
the correct subset of targets. Ensure that the correct rewrite_labels is configured

.. code-block:: yaml

    - job_name: 'promgen'
      file_sd_configs:
        - files:
          - "/etc/prometheus/promgen.json"
      relabel_configs:
      - source_labels: [__shard]
        # Our regex value here should match the shard name (exported as __shard)
        # that shows up in Promgen. In the case we want our Prometheus server to
        # scrape all targets, then we can omit the relable config.
        regex: promshard
        action: keep
