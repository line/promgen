# Copyright (c) 2026 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import logging

from django import forms

from promgen import util
from promgen.notification import NotificationBase

logger = logging.getLogger(__name__)


class FormAlertmanager(forms.Form):
    value = forms.URLField(
        required=True,
        label="URL",
        help_text="URL to Alertmanager's Alerts API end point.",
    )
    alias = forms.CharField(
        required=False,
        help_text="Optional description to be displayed instead of the URL.",
    )


class NotificationAlertmanager(NotificationBase):
    """
    Send Promgen-managed alerts directly to user's Alertmanager instances.
    """

    form = FormAlertmanager

    def _send(self, url, data):
        alerts = data.get("alerts", [])
        if alerts:
            # Convert to Alertmanager format
            # https://github.com/prometheus/alertmanager/blob/main/api/v2/openapi.yaml#L459
            alertmanager_json = [
                {
                    k: alert.get(k)
                    for k in ("startsAt", "endsAt", "annotations", "labels", "generatorURL")
                    if k in alert
                }
                for alert in alerts
            ]
            util.post(url, json=alertmanager_json).raise_for_status()
