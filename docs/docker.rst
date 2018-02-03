Running with Docker
===================

The easiest way to get started is by using
`docker-compose <https://docs.docker.com/compose/>`__.

Promgen ships with two ``docker-compose.yml`` files:

-  For running the backend, i.e. the mariadb and redis databases
   (``docker/backend`` folder).
-  For running the Promgen web app, Promgen worker, Prometheus, Alertmanger and
   the `Blackbox exporter <https://github.com/prometheus/blackbox_exporter>`__
   (``.``, the repo's root folder).

Start by cloning the repository and checkout a released version
(e.g. tag ``v0.26``), then execute the following commands in the repo's root
folder.

.. code-block:: sh

    # Start backend (mariadb and redis)
    cd docker/backend
    docker-compose up -d
    cd ../..

    # Bootstrap configuration
    mkdir promgen prometheus
    cp docker/prometheus.yml prometheus
    cp promgen/tests/examples/promgen.yml promgen

    # Run database migrations
    docker-compose run --rm web migrate

    # Register the prometheus instance
    docker-compose run --rm web register default prometheus 9090

    # Create a new superuser
    docker-compose run --rm web createsuperuser

    # Start promgen and prometheus containers
    docker-compose up -d

Promgen is now configured and can be accessed via its web interface.

These services are accessible when all containers are running:

-  Promgen Web: http://localhost:8000
-  Prometheus: http://localhost:9090
-  Alertmanager: http://localhost:9093

The following commands also prove useful:

.. code-block:: sh

    # View the logs
    docker-compose logs
    # View and follow the logs, stop with Ctrl-C
    docker-compose logs -f

    # Stop promgen
    docker-compose stop
    # Stop backend
    cd docker/backend
    docker-compose stop
    cd ../..

    # Remove promgen containers
    docker-compose rm
    # Remove backend containers
    cd docker/backend
    docker-compose rm
    cd ../..

    # Prune docker volumes
    docker volume prune
