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
