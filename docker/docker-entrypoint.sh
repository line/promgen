#!/bin/bash

set -e

if [ "${1:0:1}" = '-' ]; then
	set -- promgen "$@"
fi

case "$1" in
docker-compose-bootstrap)
  # Shortcut to wait for database to startup and run migrations
  until promgen check 2>/dev/null
  do
    echo "Waiting for database to startup"
    sleep 3
  done
  promgen migrate
  promgen register docker-demo prometheus 9090
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
bootstrap|createsuperuser|migrate|shell|test|import|queuecheck|rbimport|register|rules|targets|urls)
  # Shortcuts for some commonly used django commands
  set -- promgen "$@"
  ;;
esac

# Finally exec our command
exec "$@"
