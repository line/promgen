#!/bin/sh

function check_migrate() {
  : "${PROMGEN_DISABLE_MIGRATE:=0}"
  # These env vars are used as parameters when registering a new shard.
  # Set defaults:
  : "${PROMGEN_REGISTER_SHARD:=docker-demo}"
  : "${PROMGEN_REGISTER_HOST:=prometheus}"
  : "${PROMGEN_REGISTER_PORT:=9090}"

  if [ ! "${PROMGEN_DISABLE_MIGRATE}" = "1" ]; then
    set -x

    promgen migrate
    promgen register "${PROMGEN_REGISTER_SHARD}" "${PROMGEN_REGISTER_HOST}" "${PROMGEN_REGISTER_PORT}"

    set +x
  fi
}

function copy_static() {
  if [ ! -f /srv/promgen/www/static/.present ]; then
    echo "Copying static files to /srv/promgen/www/static..."
    set -x

    mkdir -p /srv/promgen/www/static
    cp -ra /usr/src/app/static /srv/promgen/www
    touch /srv/promgen/www/static/.present

    set +x
  fi
}

set -e

if [ "${1:0:1}" = '-' ]; then
  set -- promgen "$@"
fi

case "$1" in
web)
  # Shortcut for launching a Promgen web worker under gunicorn
  shift

  until promgen check 2>/dev/null
  do
    echo "Waiting for database to startup"
    sleep 3
  done

  copy_static
  migrate

  set -- gunicorn "promgen.wsgi:application" --bind 0.0.0.0:8000 "$@"
  ;;
web-dev)
  # Shortcut for launching a Promgen web worker under gunicorn
  shift

  until promgen check 2>/dev/null
  do
    echo "Waiting for database to startup"
    sleep 3
  done

  copy_static
  migrate

  set -- promgen runserver 0.0.0.0:8000 "$@"
  ;;
worker)
  # Shortcut to start a celery worker for Promgen
  set -- celery "-A" promgen "$@"
  ;;
init-config)
  shift

  exec promgen bootstrap --noinput "$@"

  if [ $(id -u) -eq '0' ]; then
    echo "Running as root, setting file permissions"

    set -x

    mkdir -p /srv/promgen/www/static
    chown promgen:promgen /srv/promgen/www/static

    mkdir -p /etc/prometheus

    touch /etc/prometheus/promgen.json /etc/prometheus/promgen.rule.yml /etc/prometheus/blackbox.json

    chown root:promgen /etc/prometheus/promgen.json /etc/prometheus/promgen.rule.yml /etc/prometheus/blackbox.json
    chmod g+rw /etc/prometheus/promgen.json /etc/prometheus/promgen.rule.yml /etc/prometheus/blackbox.json

    set +x
  fi

  ;;
bootstrap|createsuperuser|migrate|shell|test|import|queuecheck|rbimport|register|rules|targets|urls)
  # Shortcuts for some commonly used django commands
  set -- promgen "$@"
  ;;
esac

# Finally exec our command
exec "$@"
