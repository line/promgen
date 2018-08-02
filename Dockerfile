FROM python:3.5.5-alpine
LABEL maintainer=paul.traylor@linecorp.com

ARG PROMETHEUS_VERSION=2.3.2
ARG PROMETHEUS_DOWNLOAD_URL=https://github.com/prometheus/prometheus/releases/download/v${PROMETHEUS_VERSION}/prometheus-${PROMETHEUS_VERSION}.linux-amd64.tar.gz

COPY docker/requirements.txt /tmp/requirements.txt
COPY setup.py /usr/src/app/setup.py
COPY promgen /usr/src/app/promgen
COPY promgen/tests/examples/promgen.yml /etc/promgen/promgen.yml
COPY docker/docker-entrypoint.sh /docker-entrypoint.sh

WORKDIR /usr/src/app

ENV PYTHONUNBUFFERED=1 \
	PROMGEN_CONFIG_DIR=/etc/promgen \
	STATIC_ROOT=/srv/promgen/www/static

RUN set -ex; \
	addgroup -g 16395 promgen; \
	adduser -D -u 16395 -G promgen promgen; \
	apk add --no-cache --update mariadb-dev; \
	apk add --no-cache --update --virtual .build build-base; \
	apk add --no-cache --update --virtual .download curl tar; \
	curl -L -s $PROMETHEUS_DOWNLOAD_URL \
		| tar -xz -C /usr/local/bin --strip-components=1 prometheus-${PROMETHEUS_VERSION}.linux-amd64/promtool; \
	pip install --no-cache-dir -r /tmp/requirements.txt; \
	pip install --no-cache-dir -e .; \
	apk del .download .build; \
	rm -rf /var/cache/apk; \
	SECRET_KEY=1 STATIC_ROOT=/usr/src/app/static promgen collectstatic --noinput;

USER promgen:promgen

EXPOSE 8000

VOLUME ["/etc/promgen", "/etc/prometheus", "/srv/promgen/www"]
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["web"]
