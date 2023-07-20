FROM python:3.9-alpine
LABEL maintainer=paul.traylor@linecorp.com

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PIP_NO_CACHE_DIR off
ENV PROMGEN_CONFIG_DIR=/etc/promgen

RUN adduser -D -u 1000 promgen promgen

# Upgrade Pip
RUN pip install --no-cache-dir -U pip~=23.2

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

RUN mkdir -p /etc/prometheus; \
    mkdir -p /etc/promgen; \
    mkdir -p /usr/src/app; \
    chown promgen /etc/prometheus

# Get needed prometheus binaries
COPY --from=prom/prometheus:v2.26.0 /bin/promtool /usr/local/bin/promtool

COPY docker/requirements.txt /tmp/requirements.txt

RUN set -ex \
    && apk add --no-cache --virtual build-deps build-base libffi-dev \
    && pip install --no-cache-dir -r /tmp/requirements.txt \
    && apk del build-deps

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
