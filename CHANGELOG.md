# Changelog

## v0.22.1

* [BUGFIX] Fix double escaped links in alerts

## v0.22

* [IMPROVEMENT] Add test button to test exporters from Promgen
* [IMPROVEMENT] Further simplify notifications by dedeuplicating labels/annotations
* [BUGFIX] Ensure we properly raise Exceptions if a sender fails
* [IMPROVEMENT] Urlize comments in Silence list (for linking to bug tracker)
* [IMPROVEMENT] Add description field to rules so developers can add additional context
* [IMPROVEMENT] Update Django to 1.11


## v0.21

* [BUGFIX] Fix headers for Prometheus Proxy
* [IMPROVEMENT] Add description field to Project and Service for adding additional context information
* [IMPROVEMENT] Add filters to audit log, so that history can be filtered by object
* [IMPROVEMENT] Add owner field to Notifier object for security auditing purposes

## v0.20

* [BUGFIX] Return upstream Prometheus error when proxying requests
* [IMPROVEMENT] Notifications are grouped as they are received from Alert Manager
* [IMPROVEMENT] Refactor Alerts to be rendered mostly client side
* [IMPROVEMENT] Refactor search page to accept searches from Grafana links
* [IMPROVEMENT] Refactored Farm buttons to better indicate local (promgen) or remote

## Rewrite
*  Rewrote in Django and Celery
  * Use Django to take advantage of more robust ORM and admin site.
  * Use Celery for writing configuration files to Prometheus nodes. This allows
    us to decouple the Promgen webui from the Prometheus nodes themselves and
    gives us better auditing when writing out the configuration files.
  * Support for using Celery to send out notifications instead of blocking a
    single thread
  * Optionally use Sentry for debugging exceptions from within Promgen
  * Take advantage of Python's setuptools endpoints for easier plugin management
* [IMPROVEMENT] Senders can be set for both Projects and Services
* [IMPROVEMENT] Improved rule editor
  * More easily edit labels and annotations on rules
  * Button to test query against Prometheus to help testing
* [IMPROVEMENT] Shard support. Supports assigning services to different shards
  for capacity management
* [IMPROVEMENT] Better support for writing sender plugins by using Python's
  setuptools framework
* [IMPROVEMENT] Blackbox exporter support by adding URLs to Project pages
* [IMPROVEMENT] Support toggling Rules and Exporters
