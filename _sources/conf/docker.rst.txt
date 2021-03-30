Running with Docker
===================


.. code-block:: sh

    # Configure custom settings, database settings, etc
    vim /etc/promgen/settings.yml
    vim /etc/promgen/CELERY_BROKER_URL
    vim /etc/promgen/DATABASE_URL
    vim /etc/promgen/SECRET_KEY

    # Running a Promgen Web worker
    docker run -d --name promgen -p 8000:8000 --network host -v /etc/promgen/:/etc/promgen/ promgen:latest web

    # Running a Promgen Alert Worker
    # Alert workers do not specify a queue and use the celery default queue
    docker run -d --name promgen --network host -v /etc/promgen/:/etc/promgen/ -v /etc/prometheus:/etc/prometheus promgen:latest worker

    # Running a Promgen Celery worker to update Prometheus settings
    # Assuming our Prometheus node is called prometheus-001 we should subscribe
    # to a celery queue with the same name that is registered in Promgen
    docker run -d --name promgen --network host -v /etc/promgen/:/etc/promgen/ -v /etc/prometheus:/etc/prometheus promgen:latest worker --queues prometheus-001
