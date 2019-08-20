#!/bin/sh

set -e

if [ "${1:0:1}" = '-' ]; then
	set -- promgen "$@"
fi

case "$1" in
docker-compose-bootstrap)
  # Shortcut to wait for database to startup and run migrations

  # These env vars are used as parameters when registering a new shard.
  # Set defaults:
  : "${PROMGEN_REGISTER_SHARD:=docker-demo}"
  : "${PROMGEN_REGISTER_HOST:=prometheus}"
  : "${PROMGEN_REGISTER_PORT:=9090}"

  until promgen check 2>/dev/null
  do
    echo "Waiting for database to startup"
    sleep 3
  done

  promgen migrate
  promgen register-server "${PROMGEN_REGISTER_SHARD}" "${PROMGEN_REGISTER_HOST}" "${PROMGEN_REGISTER_PORT}"
  promgen loaddata exporters
  exit 0
  ;;
worker)
  # Shortcut to start a celery worker for Promgen
  set -- celery "-A" promgen "$@"
  ;;
web)
  # Shortcut for launching a Promgen web worker under gunicorn
  shift
  set -- gunicorn "promgen.wsgi:application" "$@"
  ;;
bootstrap|createsuperuser|migrate|shell|test|import|queuecheck|rbimport|register-server|register-exporter|rules|targets|urls)
  # Shortcuts for some commonly used django commands
  set -- promgen "$@"
  ;;
esac

# Finally exec our command
exec "$@"
