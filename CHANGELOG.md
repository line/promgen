# Changelog

# v0.51 - Unreleased

# v0.50 - 2021-03-03

- [IMPROVEMENT] Improved Alert detail view #313
- [BUGFIX] Move checks that require database, to post_migrate #314

# v0.49 - 2021-02-02

- [BUGFIX] Fix some timezone display bugs for alerts page and silence menus #306
- [BUGFIX] Fix typo in 'No results' message #292
- [BUGFIX] Split bootstrap checks to avoid check errors #303
- [DOCUMENTATION] Add note about reporting vulnerability #298
- [DOCUMENTATION] Update install docs to mention Makefile #299
- [IMPROVEMENT] Link back to Promgen in processed alert #307

# v0.48 - 2020-07-21

- [BUGFIX] Fix checks that rely on database connection #280
- [BUGFIX] Fix overflow formatting for notifiers #290
- [BUGFIX] Use alternate Vue delimiters to fix double rendering bugs #288
- [INTERNAL] Bump django from 2.2.10 to 2.2.13 #284

# v0.47 - 2020-05-14

- [BUGFIX] Fix our check warning messages #277
- [BUGFIX] Add scroll bar to notifier table #273
- [INTERNAL] Refactoring and cleaning up `promgen bootstrap` #270
- [ENHANCEMENT] Use the django checks framework to diagnose common errors #271
- [ENHANCEMENT] Select multiple servers to silence #268

# v0.46 - 2020-04-01

Breaking

Promgen no longer defaults `ALLOWED_HOSTS = ['*']` so deployments should set it properly.
You can also export `ALLOWED_HOSTS=*` to disable this check

See: https://docs.djangoproject.com/en/2.2/ref/settings/#std:setting-ALLOWED_HOSTS

- [BUGFIX] Fix unique_together for Exporter #267
- [BUGFIX] Fix Makefile command #265
- [BUGFIX] Fix exporter test button #263
- [BUGFIX] Fix missing scheme on default exporter #259
- [BUGFIX] Fix test data for notifier test #257
- [BUGFIX] Fix missing error message with duplicate Rule name #254
- [BUGFIX] Fix race condition between process and index alerts #251 #250
- [ENHANCEMENT] Allow toggling notifiers #258
- [ENHANCEMENT] Allow quick access to Prometheus ui from Project #252

# v0.45 - 2020-03-02

- [BUGFIX] Update to redirect to correct location #246
- [ENHANCEMENT] Allow filtering alerts on alert list page #242
- [INTERNAL] Cleanup some minor migration issues #241
- [INTERNAL] Clenaup test cases #243
- [INTERNAL] Helper to rewrite query string for paginated lists #244
- [INTERNAL] Refactoring help_text #237
- [INTERNAL] Rename commands to better group similar functionality #247
- [INTERNAL] Update circleci config #245

## v0.44 - 2020-02-21

- [BUGFIX] Add missing duration label to rules page #238
- [BUGFIX] Fix for labelvalues #234, #240
- [ENHANCEMENT] Support http/https when configuring exporters #235

## v0.43 - 2020-02-12

- [BUGFIX] Fix login redirect with social auth #230
- [BUGFIX] Add validation to Shard, Service, Project, and Farm name #228
- [INTERNAL] Start refactoring api into `/rest/` namespace #224
- [BUGFIX] Fixes to unit tests to avoid signal errors #216
- [DOCUMENTATION] Fix reference to old endpoint #206

## v0.42 - 2019-12-03

- [BUGFIX] Pin kombu to 4.6.3 to fix bug with redis exchange #197
- [IMPROVEMENT] Show read-only view of incoming alerts #199
- [IMPROVEMENT] Tracking for failed alerts #200
- [INTERNAL] Refactor Metrics collector #201

## v0.41 - 2019-11-12

- [BUGFIX] Catch ConnectionError and RequestException for better results #191
- [BUGFIX] Rule.content_object should use our Site proxy module #194
- [BUGFIX] Update test data for Alertmanager #196
- [IMPROVEMENT] Add `promgen register-host` to register host from command line #193
- [IMPROVEMENT] Add `promgen register-job` to register job from command line #192

## v0.40 - 2019-10-28

- [BUGFIX] Disable button when no farm assigned #188
- [BUGFIX] Fix hostname validation #181
- [BUGFIX] Fix HTTP 405 when updating a rule #176
- [BUGFIX] Fix output from `promgen rules` command #186
- [BUGFIX] Fix rule import #189
- [BUGFIX] Fixes for Docker build #174
- [BUGFIX] pk should always be an integer #178
- [CHANGE] Rewrite exporter test button in Vue #187
- [DOCUMENTATION] Fix method for route #185
- [IMPROVEMENT] Add custom promql-query tag #184
- [IMPROVEMENT] Settings helper for Promgen config #183
- [INTERNAL] Refactor unittests #166
- [INTERNAL] Upgrade Django to 2.2.4 #175

Breaking

- `config_writer:path` changes to `prometheus:targets`
- `alert_blacklist` changes to `alertmanager:blacklist`

See `promgen/tests/examples/promgen.yml`

## v0.39 - 2019-08-19

- [BUGFIX] Fix queries for promgen.Rule and promgen.Site #170
- [BUGFIX] Fix rule import for Project/Service #165
- [BUGFIX] Migrate from sites.site to promgen.site to fix references #164
- [IMPROVEMENT] Add PROMGEN_SCHEME to support https links #160
- [IMPROVEMENT] Add silence button to blackbox exporter entries #156
- [IMPROVEMENT] Import probe config from blackbox_exporter #155
- [IMPROVEMENT] Read-only rule page #169
- [INTERNAL] Cleanup URL paths #167
- [INTERNAL] Minor version updates and Dockerfile cleanup #163
- [INTERNAL] Refactor apk commands in Dockerfile #172
- [INTERNAL] Refactor macro for common use case #168
- [INTERNAL] Remove fragile celery metrics #171

## v0.38 - 2019-07-03

- [CHANGE] Remove old Prometheus v1 rule format #148
- [IMPROVEMENT] Support selecting probe module for blackbox monitoring #154
- [IMPROVEMENT] When listing rules, show rule specific labels #153

Setting for `url_writer` changes to `prometheus:blackbox`

See `promgen/tests/examples/promgen.yml`

## v0.37 - 2019-06-17

- [INTERNAL] Upgrade to Django 2.2.x #152
- [BUGFIX] Fix rule rendering table on host detail page #151
- [BUGFIX] Fix rendering errors with Silence/Alert dropdowns #150
- [BUGFIX] Fix search page rendering #149
- [INTERNAL] Move remaining celery tasks to tasks.py #139

## v0.36 - 2019-05-29

- [CHANGE] Refactor shard assignment from service to Project #147

## v0.35 - 2019-04-16

- [BUGFIX] Refactor rule validation to take into account labels and annotations #144
- [BUGFIX] Move promtool validation into RuleForm.clean #142
- [INTERNAL] Update various dependencies #143
- [IMPROVEMENT] Add proxy for /api/v1/labels #140
- [IMPROVEMENT] Use django-filters for api filtering #126

## v0.34 - 2019-03-13

This release adds support for filters for notifications. Alerts can be filtered so that different notification targets can be restricted by label. For example, sending urgent messages directly to LINE but sending less urgent messages to be logged to slack

- [INTERNAL] Refactor how we proxy errors #136
- [BUGFIX] Fix arguments for create/filter/get_or_create #137
- [BUGFIX] Fix filterActiveSilences condition #135
- [FEATURE] Implement sender whitelist filters #132
- [INTERNAL] Refactor Breadcrumb from template to simple_tag #133
- [INTERNAL] Refactor manager class and validators #131

## v0.33 - 2019-03-01

- [BUGFIX] Fix computed labels #129
- [BUGFIX] Fix validation of silence duration #130
- [IMPROVEMENT] Add logo + favicon #128
- [IMPROVEMENT] Various page query optimizations #127

## v0.32 - 2019-02-22

- [IMPROVEMENT] Add button to silence a single alert #125
- [CHANGES] Rewritten display of alerts and silences to use vuejs #124
- [INTERNAL] Split proxy views to their own module #123
- [IMPROVEMENT] Add default notifier when subscribing #122
- [BUGFIX] Validate URL field for notifications #121
- [ENHANCEMENT] Improvements to Admin Alert view #116

## v0.31 - 2018-12-05

- [BUGFIX] Ensure that invalid annotations are caught #113
- [CHANGES] Bump Python to 3.6 and use Pipfile for easier development onboarding #109
- [CHANGES] Update Django version #107
- [ENHANCEMENT] Add 'owner' field for Projects and Services #111
- [ENHANCEMENT] Initial read-only API provided by django-rest-framework #112
- [ENHANCEMENT] New homepage to show subscribed services #105
- [ENHANCEMENT] Refactor to support Project and Site rule exports #104
- [ENHANCEMENT] Support adding exporter defaults from admin gui #114

## v0.30 - 2018-10-02

- [BUGFIX] Fix for missing promtool validation error #103
- [BUGFIX] Fix reference to self.get_object() in RuleToggle #99
- [CHANGE] Refactor notifications queue for audibility and reliability #94
- [CHANGE] Add prune-alerts command #106

This version refactors the alert sender queue to better separate responsibility between components and to provide a more auditable record of received alerts

## v0.29 - 2018-08-28

- [IMPROVEMENT] Implement Django permissions for Rule editor #96

This first version implements permissions primarily for common, shared rules to reduce the chance of accidentally modifying the parent rule. In the future, permissions will be applied to more objects. Migrations will automatically create a Default group in the Django admin.

## v0.28 - 2018-08-01

- [CHANGE] Update to Django 2.0 #82
- [CHANGES] Re-add link to shard #91
- [IMPROVEMENT] Add /api/v1/query proxy #88
- [IMPROVEMENT] Add help text describing job label usage #93
- [IMPROVEMENT] RuleTest will test against all Prometheus instances #90

## v0.27 - 2018-06-14

- [BUGFIX] Fix parsing error with silence end date
- [BUGFIX] Fix webhook POST data
- [CHANGE] Update Celery version for bug fix
- [IMPROVEMENT] Cleanup some page headers to make navigation easier
- [IMPROVEMENT] Simple proxy page for `/graph` view
- [IMPROVEMENT] Speed up services page with prefetch_related_objects
- [IMPROVEMENT] Support entering comma separated list of hosts
- [IMPROVEMENT] Support for disabling a shard (disables adding new services)
- [IMPROVEMENT] Use css grid to improve readability of long pages
- [IMPROVEMENT] Warn if parent rull is missing macro

## v0.26 - 2018-03-12

- [BUGFIX] Allow STATIC_ROOT to be configured via Environment
- [BUGFIX] Fix bytes/string mismatch with outputing rules
- [BUGFIX] Fix error message when registering a duplicate Service
- [BUGFIX] Fix missing list of exporters on host detail page
- [BUGFIX] Fix typo in view names
- [CHANGE] Bootstrap default admin user when starting Promgen with an empty database
- [CHANGE] Change handling of DEBUG variable. Now requires that a value is set in /path/DEBUG instead of just the file existing
- [CHANGE] CONFIG_DIR renamed to PROMGEN_CONFIG_DIR
- [CHANGE] Temporarily disable typeahead plugin pending refactoring
- [IMPROVEMENT] Added Slack notifier
- [IMPROVEMENT] Ship promtool in docker image
- [IMPROVEMENT] Updates to documentation

## v0.25

- [BUGFIX] Fix formatting on yaml rules file to output as unicode
- [BUGFIX] Minor optimization for admin page
- [BUGFIX] Include missing package data
- [BUGFIX] Fix double slash with exporter path test
- [IMPROVEMENT] Add default project/service label when creating new rule
- [IMPROVEMENT] Show disabled exporters as light grey
- [IMPROVEMENT] Show confirmation when toggling exporter

## v0.24

- [BUGFIX] Minor permissions fix with atomic_write method
- [IMPROVEMENT] Remove special 'default' group and support Site as a parent for shared rules
- [IMPROVEMENT] Add support for Prometheus 2.x rule format (yaml rules)
- [IMPROVEMENT] Fix getting started documentation with Docker
- [BUGFIX] Add test cases for alert manager silence
- [BUGFIX] Switch to Django's builtin LoginRequiredMixin to handle auth
- [CHANGE] remove 'rule_writer' stanza from config and mere into 'prometheus' stanza

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

- [BUGFIX] Fix double escape regression
- [BUGFIX] Fix host silence tag on search page
- [IMPROVEMENT] Minor query speedup for Admin pages
- [IMPROVEMENT] Support 'User' notifications. User's can be set as a notification target and Users can configure their own subscriptions from a profile page

## v0.22

- [IMPROVEMENT] Add test button to test exporters from Promgen
- [IMPROVEMENT] Further simplify notifications by deduplicating labels/annotations
- [BUGFIX] Ensure we properly raise Exceptions if a sender fails
- [IMPROVEMENT] Urlize comments in Silence list (for linking to bug tracker)
- [IMPROVEMENT] Add description field to rules so developers can add additional context
- [IMPROVEMENT] Update Django to 1.11

## v0.21

- [BUGFIX] Fix headers for Prometheus Proxy
- [IMPROVEMENT] Add description field to Project and Service for adding additional context information
- [IMPROVEMENT] Add filters to audit log, so that history can be filtered by object
- [IMPROVEMENT] Add owner field to Notifier object for security auditing purposes

## v0.20

- [BUGFIX] Return upstream Prometheus error when proxying requests
- [IMPROVEMENT] Notifications are grouped as they are received from Alert Manager
- [IMPROVEMENT] Refactor Alerts to be rendered mostly client side
- [IMPROVEMENT] Refactor search page to accept searches from Grafana links
- [IMPROVEMENT] Refactored Farm buttons to better indicate local (promgen) or remote

## Rewrite

- Rewrote in Django and Celery

  - Use Django to take advantage of more robust ORM and admin site.
  - Use Celery for writing configuration files to Prometheus nodes. This allows us to decouple the Promgen webui from the Prometheus nodes themselves and gives us better auditing when writing out the configuration files.
  - Support for using Celery to send out notifications instead of blocking a single thread
  - Optionally use Sentry for debugging exceptions from within Promgen
  - Take advantage of Python's setuptools endpoints for easier plugin management

- [IMPROVEMENT] Senders can be set for both Projects and Services
- [IMPROVEMENT] Improved rule editor

  - More easily edit labels and annotations on rules
  - Button to test query against Prometheus to help testing

- [IMPROVEMENT] Shard support. Supports assigning services to different shards for capacity management
- [IMPROVEMENT] Better support for writing sender plugins by using Python's setuptools framework
- [IMPROVEMENT] Blackbox exporter support by adding URLs to Project pages
- [IMPROVEMENT] Support toggling Rules and Exporters
