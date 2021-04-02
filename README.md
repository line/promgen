# What is Promgen?

Promgen is a configuration file generator for [Prometheus](https://prometheus.io). Promgen is a web application written with [Django](https://docs.djangoproject.com/en/1.10/) and can help you do the following jobs.

- Create and manage Prometheus configuration files
- Configure alert rules and notification options

See the [Promgen introduction slides](https://www.slideshare.net/tokuhirom/promgen-prometheus-managemnet-tool-simpleclientjava-hacks-prometheus-casual) for the original history of Promgen.

See https://line.github.io/promgen/ for additional documentation.

## Promgen screenshots

![screenshot](docs/images/screenshot.png)

## Contributing

Below are the steps to get started with Promgen.

Please see [CONTRIBUTING.md](https://github.com/line/promgen/blob/master/CONTRIBUTING.md) for contributing to Promgen.

If you believe you have discovered a vulnerability or have an issue related to security, please DO NOT open a public issue. Instead, send us a mail to dl_oss_dev@linecorp.com.

### 1. Initialize Promgen

Initialize Promgen using Docker.

```bash
# Create promgen setting directory.
mkdir -p ~/.config/promgen
chmod 777 ~/.config/promgen

# Initialize required settings with Docker container
# This will prompt you for connection settings for your database and Redis broker
# using the standard DSN syntax.
# Database example: mysql://username:password@hostname/databasename
# Broker example: redis://localhost:6379/0
docker run --rm -it -v ~/.config/promgen:/etc/promgen/ line/promgen bootstrap

# Apply database updates
docker run --rm -v ~/.config/promgen:/etc/promgen/ line/promgen migrate

# You can then check your configuration to ensure everything correct
docker run --rm -v ~/.config/promgen:/etc/promgen/ line/promgen check

# Create initial login user. This is the same as the default django-admin command
# https://docs.djangoproject.com/en/1.10/ref/django-admin/#django-admin-createsuperuser
docker run --rm -it -v ~/.config/promgen:/etc/promgen/ line/promgen createsuperuser
```

You can then use your favorite configuration management system to deploy to each worker.

> Note: Promgen aims to use the [XDG](https://specifications.freedesktop.org/basedir-spec/latest/ar01s03.html) specs and follows suggestions made by the [12-Factor App](https://12factor.net/).

### 2. Configure Prometheus

Configure Prometheus to load the target file from Prometheus and configure AlertManager to send notifications back to Promgen.

See the example settings files for proper configuration of Prometheus and AlertManager.

- [Example settings file](promgen/tests/examples/promgen.yml)
- [Example Prometheus file](docker/prometheus.yml)
- [Example AlertManager file](docker/alertmanager.yml)

### 3. Run Promgen

Run Promgen using the following command.

```bash
# Run Promgen web worker. This is typically balanced behind an NGINX instance
docker run --rm -p 8000:8000 -v ~/.config/promgen:/etc/promgen/ line/promgen

# Run Promgen celery worker. Make sure to run it on the same machine as your Prometheus server to manage the config settings
docker run --rm -v ~/.config/promgen:/etc/promgen/ -v /etc/prometheus:/etc/prometheus line/promgen worker

# Or if using docker-compose you can spin up a complete test environment
docker-compose up -d
# Create initial user
docker-compose run web createsuperuser
```

## The MIT License

Copyright (c) 2017 LINE Corporation

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
