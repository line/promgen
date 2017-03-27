Running Promgen using Docker
============================


.. code-block:: sh

    # Configure custom settings, database settings, etc
    vim /etc/promgen/settings.yml
    vim /etc/promgen/CELERY_BROKER_URL
    vim /etc/promgen/DATABASE_URL
    vim /etc/promgen/SECRET_KEY

    # Running a Promgen Django worker
    docker run -d --name promgen -p 8000:8000 --network host -v /etc/promgen/:/etc/promgen/ promgen:latest

    # Running a Promgen Celery worker
    docker run -d --name promgen --network host -v /etc/promgen/:/etc/promgen/ -v /etc/prometheus:/etc/prometheus promgen:latest celery
