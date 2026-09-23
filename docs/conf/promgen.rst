Configuring Promgen
===================

Promgen Settings are configurable by creating a ``PROMGEN_CONFIG`` file (default is ``promgen.yml``)
in the ``PROMGEN_CONFIG_DIR`` directory (default is ``~/.config/promgen/``), or via environment variables.

The following settings are available:

.. contents::
   :local:
   :depth: 1


API_TOKEN_MAX_QUOTA
-------------------
[Integer | default = None]

Number of tokens a user is allowed to create. The default is None, which means unlimited.


API_TOKEN_TTL_DAYS
-------------------
[Integer | default = None]

Maximum number of days an API token is valid for. When set, Promgen will not allow the creation of
API tokens with expiry greater than this setting. The default is None, which means unlimited.


CELERY_ENABLE_PROMGEN_DEAD_LETTER_QUEUE
---------------------------------------
[Boolean | default = False]

When enabled, retried tasks (See: :ref:`queue`) will be moved to a separate dead-letter queue named
"promgen_dlq" instead of sending them back to the original queue. (See: :ref:`dlq`)


PROMGEN_EXPORTER_SCRAPE_TIMEOUT
-------------------------------
[Integer | default = 25]

Maximum time to wait for all scraping operations of Project's exporters to complete (in seconds).


V2_API_LOGGING_ENABLED
-----------------------
[Boolean | default = True]

This setting enables logging of all V2 API requests and responses, providing a clear record of
actions performed through these APIs.

For requests, the method, path, and request body are logged. However, fields in the request body
are truncated to avoid filling up the log. By default, the character limit is set to 128, but fields
like "clause" are still logged in full as they are necessary. For responses, only the status and
response content size are logged. A unique trace ID is generated to link the request and response logs.
