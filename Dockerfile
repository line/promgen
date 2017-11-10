FROM python:3.5.3-alpine
MAINTAINER paul.traylor@linecorp.com

RUN adduser -D -u 1000 promgen promgen
RUN apk add --no-cache --update mariadb-dev build-base bash && \
    rm -rf /var/cache/apk/*

ENV PYTHONUNBUFFERED 1
ENV PIP_NO_CACHE_DIR off

RUN mkdir -p /etc/prometheus
RUN mkdir -p /etc/promgen
RUN mkdir -p /usr/src/app
RUN chown promgen /etc/prometheus

RUN apk add --no-cache wget && wget https://github.com/prometheus/prometheus/releases/download/v1.8.2/prometheus-1.8.2.linux-arm64.tar.gz
RUN tar xvzf prometheus-1.8.2.linux-arm64.tar.gz
RUN cp prometheus-1.8.2.linux-arm64/promtool /usr/local/bin/promtool

COPY docker/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

COPY setup.py /usr/src/app/setup.py
COPY promgen /usr/src/app/promgen
COPY promgen/tests/examples/promgen.yml /etc/promgen/promgen.yml

WORKDIR /usr/src/app
RUN pip install -e .

ENV CONFIG_DIR=/etc/promgen

USER promgen
EXPOSE 8000

RUN SECRET_KEY=1 promgen collectstatic --noinput

COPY docker/docker-entrypoint.sh /
VOLUME ["/etc/promgen", "/etc/prometheus"]
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["web", "--bind", "0.0.0.0:8000", "--workers", "4"]
