FROM python:3.5.3-alpine
MAINTAINER paul.traylor@linecorp.com

ENV PROMETHEUS_VERSION 2.1.0
ENV PROMETHEUS_DOWNLOAD_URL https://github.com/prometheus/prometheus/releases/download/v${PROMETHEUS_VERSION}/prometheus-${PROMETHEUS_VERSION}.linux-amd64.tar.gz

RUN adduser -D -u 1000 promgen promgen
RUN apk add --no-cache --update mariadb-dev build-base bash && \
    rm -rf /var/cache/apk/*

RUN set -ex; \
        apk add --no-cache curl tar; \
        curl -L -s $PROMETHEUS_DOWNLOAD_URL \
		| tar -xz -C /usr/local/bin --strip-components=1 prometheus-${PROMETHEUS_VERSION}.linux-amd64/promtool; \
        apk del curl tar; \
	rm -rf /var/cache/apk;

ENV PYTHONUNBUFFERED 1
ENV PIP_NO_CACHE_DIR off

RUN mkdir -p /etc/prometheus
RUN mkdir -p /etc/promgen
RUN mkdir -p /usr/src/app
RUN chown promgen /etc/prometheus

COPY docker/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

COPY setup.py /usr/src/app/setup.py
COPY promgen /usr/src/app/promgen
COPY promgen/tests/examples/promgen.yml /etc/promgen/promgen.yml

WORKDIR /usr/src/app
RUN pip install -e .

ENV PROMGEN_CONFIG_DIR=/etc/promgen

USER promgen
EXPOSE 8000

RUN SECRET_KEY=1 promgen collectstatic --noinput

COPY docker/docker-entrypoint.sh /
VOLUME ["/etc/promgen", "/etc/prometheus"]
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["web", "--bind", "0.0.0.0:8000", "--workers", "4"]
