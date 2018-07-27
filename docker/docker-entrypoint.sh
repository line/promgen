#!/bin/bash

set -e

if [ "${1:0:1}" = '-' ]; then
	set -- promgen "$@"
fi

case "$1" in
worker)
  # Shortcut to start a celery worker for Promgen
  set -- celery "-A" promgen "$@"
  ;;
web)
  # Shortcut for launching a Promgen web worker under gunicorn
  shift
  set -- gunicorn "promgen.wsgi:application" "$@"
  ;;
wait-runserver)
  # Shortcut to wait for db and start the Promgen web app in development mode (django runserver)
  until promgen check 2>/dev/null
  do
    echo "Waiting for database to startup"
    sleep 3
  done

  shift
  set -- promgen runserver "$@"
  ;;
bootstrap|createsuperuser|migrate|shell|test|import|queuecheck|rbimport|register|rules|targets|urls)
  # Shortcuts for some commonly used django commands
  set -- promgen "$@"
  ;;
esac

# Finally exec our command
exec "$@"
