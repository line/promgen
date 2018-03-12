# Changelog

## v0.26 - 2018-03-12
* [BUGFIX] Allow STATIC_ROOT to be configured via Environment
* [BUGFIX] Fix bytes/string mismatch with outputing rules
* [BUGFIX] Fix error message when registering a duplicate Service
* [BUGFIX] Fix missing list of exporters on host detail page
* [BUGFIX] Fix typo in view names
* [CHANGE] Bootstrap default admin user when starting Promgen with an empty database
* [CHANGE] Change handling of DEBUG variable. Now requires that a value is set in /path/DEBUG instead of just the file existing
* [CHANGE] CONFIG_DIR renamed to PROMGEN_CONFIG_DIR
* [CHANGE] Temporarily disable typeahead plugin pending refactoring
* [IMPROVEMENT] Added Slack notifier
* [IMPROVEMENT] Ship promtool in docker image
* [IMPROVEMENT] Updates to documentation

## v0.25
* [BUGFIX] Fix formatting on yaml rules file to output as unicode
* [BUGFIX] Minor optimization for admin page
* [BUGFIX] Include missing package data
* [BUGFIX] Fix double slash with exporter path test
* [IMPROVEMENT] Add default project/service label when creating new rule
* [IMPROVEMENT] Show disabled exporters as light grey
* [IMPROVEMENT] Show confirmation when toggling exporter

## v0.24
* [BUGFIX] Minor permissions fix with atomic_write method
* [IMPROVEMENT] Remove special 'default' group and support Site as a parent for shared rules
* [IMPROVEMENT] Add support for Prometheus 2.x rule format (yaml rules)
* [IMPROVEMENT] Fix getting started documentation with Docker
* [BUGFIX] Add test cases for alert manager silence
* [BUGFIX] Switch to Django's builtin LoginRequiredMixin to handle auth
* [CHANGE] remove 'rule_writer' stanza from config and mere into 'prometheus' stanza

```yaml
# These are used for Promgen to automatically trigger a reload on target changes
prometheus:
  url: http://prometheus:9090/
  version: 2
  # Promtool was moved into the prometheus stanza. To skip validation this can
  # be set to the path of the 'true' binary
  promtool: /usr/local/bin/promtool
  # promtool: /usr/bin/true # to disable
  # Output rule configuration to this path
  rules: /etc/prometheus/promgen.rule.yml
  # Or remove .yml for when working with Prometheus 1.x
  # rules: /etc/prometheus/promgen.rule
# The old rule_writer format is now unused and can be deleted
#rule_writer:
#  path: /etc/prometheus/promgen.rule
#  promtool_path: /usr/local/bin/promtool
```


## v0.23
* [BUGFIX] Fix double escape regression
* [BUGFIX] Fix host silence tag on search page
* [IMPROVEMENT] Minor query speedup for Admin pages
* [IMPROVEMENT] Support 'User' notifications. User's can be set as a notification target and Users can configure their own subscriptions from a profile page

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
