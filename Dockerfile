FROM python:3.5.3-alpine
LABEL maintainer=paul.traylor@linecorp.com

ENV PROMETHEUS_VERSION 2.2.1
ENV PROMETHEUS_DOWNLOAD_URL https://github.com/prometheus/prometheus/releases/download/v${PROMETHEUS_VERSION}/prometheus-${PROMETHEUS_VERSION}.linux-amd64.tar.gz

ENV PYTHONUNBUFFERED 1
ENV PIP_NO_CACHE_DIR off

COPY docker/requirements.txt /tmp/requirements.txt
COPY setup.py /usr/src/app/setup.py
COPY promgen /usr/src/app/promgen
COPY promgen/tests/examples/promgen.yml /etc/promgen/promgen.yml
COPY docker/docker-entrypoint.sh /

WORKDIR /usr/src/app

ENV PROMGEN_CONFIG_DIR=/etc/promgen

RUN set -ex; \
	apk add --no-cache --update mariadb-dev bash; \
	apk add --no-cache --update --virtual .build build-base; \
	apk add --no-cache --update --virtual .download curl tar; \
	curl -L -s $PROMETHEUS_DOWNLOAD_URL \
		| tar -xz -C /usr/local/bin --strip-components=1 prometheus-${PROMETHEUS_VERSION}.linux-amd64/promtool; \
	mkdir -p /etc/prometheus; \
	pip install -r /tmp/requirements.txt; \
	pip install -e .; \
	apk del .download .build; \
	rm -rf /var/cache/apk; \
	SECRET_KEY=1 promgen collectstatic --noinput;

EXPOSE 8000

VOLUME ["/etc/promgen", "/etc/prometheus"]
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["web", "--bind", "0.0.0.0:8000", "--workers", "4"]
