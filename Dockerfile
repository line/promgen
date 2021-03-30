FROM python:3.6.9-alpine
LABEL maintainer=paul.traylor@linecorp.com

ENV PROMETHEUS_VERSION 2.11.1
ENV PROMETHEUS_DOWNLOAD_URL https://github.com/prometheus/prometheus/releases/download/v${PROMETHEUS_VERSION}/prometheus-${PROMETHEUS_VERSION}.linux-amd64.tar.gz
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PIP_NO_CACHE_DIR off
ENV PROMGEN_CONFIG_DIR=/etc/promgen

RUN adduser -D -u 1000 promgen promgen

# Upgrade Pip
RUN pip install --no-cache-dir -U pip==20.0.2

# Install MySQL Support
RUN set -ex \
    && apk add --no-cache mariadb-dev \
    && apk add --no-cache --virtual build-deps build-base \
    && pip --no-cache-dir install mysqlclient \
    && apk del build-deps 

# Install Postgres Support
RUN set -ex \
    && apk add --no-cache postgresql-dev \
    && apk add --no-cache --virtual build-deps build-base \
    && pip install --no-cache-dir psycopg2-binary \
    && apk del build-deps

# Install Prometheus Binary
RUN set -ex \
    && apk add --no-cache --virtual build-deps curl tar \
    && curl -L -s $PROMETHEUS_DOWNLOAD_URL \
    | tar -xz -C /usr/local/bin --strip-components=1 prometheus-${PROMETHEUS_VERSION}.linux-amd64/promtool \
    && apk del build-deps

RUN mkdir -p /etc/prometheus; \
    mkdir -p /etc/promgen; \
    mkdir -p /usr/src/app; \
    chown promgen /etc/prometheus

COPY docker/requirements.txt /tmp/requirements.txt

RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY docker/docker-entrypoint.sh /
COPY setup.py /usr/src/app/setup.py
COPY setup.cfg /usr/src/app/setup.cfg
COPY promgen /usr/src/app/promgen
COPY promgen/tests/examples/promgen.yml /etc/promgen/promgen.yml

WORKDIR /usr/src/app
RUN pip install --no-cache-dir -e .

USER promgen
EXPOSE 8000

RUN SECRET_KEY=1 promgen collectstatic --noinput

VOLUME ["/etc/promgen", "/etc/prometheus"]
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["web", "--bind", "0.0.0.0:8000", "--workers", "4"]
