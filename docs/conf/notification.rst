Configuring Notification Plugins
================================

Different settings for the Notification Plugins can be defined in the ``promgen.yml`` file.

PagerDuty
---------------------

PagerDuty API-compatible URLs and alert severity mapping can be configured this way:

.. code-block:: yaml

    promgen.notification.pagerduty:
      urls:
        PagerDuty: https://events.pagerduty.com/v2/enqueue
        OtherServer: https://compatible.pagerduty.server/api/enqueue
      severity_mapping:
        debug: info
        major: error
        minor: warning

Slack
---------------------

The proxy configuration specifies the proxy server that Promgen should use when sending
notifications to Slack. This is useful if your environment requires outgoing requests to go
through a proxy for security or network policy reasons. If your environment does not require a
proxy, you can basically ignore this setting or set it to an empty string.

.. code-block:: yaml

    promgen.notification.slack:
      proxy: http://slack-proxy.example.com:8080
