Configuring Promgen API
=======================

Promgen API configuration is configurable via environment variables.

The following settings are available:


API_TOKEN_MAX_QUOTA
-------------------
[Integer | default = None]

Number of tokens a user is allowed to create. The default is None, which means unlimited.

*This setting applies to API token creation on the Promgen Site and API endpoint but is not enforced
on the Django Admin Site. The Promgen Admin can create tokens on the Django Admin Site without restrictions.*


API_TOKEN_TTL_DAYS
-------------------
[Integer | default = None]

Maximum number of days an API token is valid for. When set, Promgen will not allow the creation of
API tokens with expiry greater than this setting. The default is None, which means unlimited.

*This setting applies to API token creation on the Promgen Site and API endpoint but is not enforced
on the Django Admin Site. The Promgen Admin can create tokens on the Django Admin Site without restrictions.*


V2_API_LOGGING_ENABLED
-----------------------
[Boolean | default = True]

This setting enables logging of all V2 API (endpoints starts with "/rest/v2/") requests and
responses, providing a clear record of actions performed through these APIs.

For requests, the method, path, and request body are logged. However, fields in the request body
are truncated to avoid filling up the log. By default, the character limit is set to 128, but fields
like "clause" are still logged in full as they are necessary. For responses, only the status and
response content size are logged. A unique trace ID is generated to link the request and response logs.
