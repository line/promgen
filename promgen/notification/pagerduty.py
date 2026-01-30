# Copyright (c) 2026 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

"""
Simple integration with PagerDuty Events V2 API.

Accepts alert json from Alert Manager and then POSTs individual alerts to PagerDuty.
"""

import logging

from django import forms

from promgen import settings, util, validators
from promgen.notification import NotificationBase
from promgen.shortcuts import resolve_domain

logger = logging.getLogger(__name__)


def _choices():
    if not getattr(settings, "PAGERDUTY_URLS", None):
        yield "PagerDuty", "PagerDuty"
    else:
        for k, v in settings.PAGERDUTY_URLS.items():
            yield (k, k)


class FormPagerDuty(forms.Form):
    domain = forms.ChoiceField(
        required=True,
        label="PagerDuty Domain",
        choices=_choices(),
    )
    integration_key = forms.CharField(
        required=True,
        label="Integration Key",
        help_text="The Integration Key (a.k.a. Routing Key) provided by PagerDuty.",
        validators=[validators.integration_key],
        widget=forms.PasswordInput(),
    )
    alias = forms.CharField(
        label="Alias",
        help_text="Description for identifying this PagerDuty integration.",
        required=True,
    )

    def clean(self):
        cleaned_data = super().clean()
        # The Sender model expects a single 'value' field. Therefore, we create it by combining
        # the domain and integration_key into a single string separated by a colon.
        cleaned_data["value"] = str.format(
            "{}:{}", cleaned_data.get("domain"), cleaned_data.get("integration_key")
        )
        return cleaned_data


class NotificationPagerDuty(NotificationBase):
    """
    Trigger an alert event to PagerDuty.
    """

    form = FormPagerDuty

    def _send(self, target, data):
        domain = target.split(":")[0]
        integration_key = target.split(":")[1]

        request_body = NotificationPagerDuty.build_request_body(data, integration_key)

        # Send event to PagerDuty Events V2 API
        # By default we send to the global endpoint unless overridden
        url = "https://events.pagerduty.com/v2/enqueue"
        if getattr(settings, "PAGERDUTY_URLS", None):
            url = settings.PAGERDUTY_URLS.get(domain)

        util.post(url, json=request_body).raise_for_status()

    @staticmethod
    def json_to_string(data):
        return "".join(f"\n - {k} = {v}" for k, v in data.items())

    @staticmethod
    def build_request_body(data, integration_key):
        # Initialize request body
        request_body = {
            "routing_key": integration_key,
            "client": "Promgen",
            "client_url": resolve_domain("home"),
        }

        # Set event action
        if data["status"] == "resolved":
            request_body["event_action"] = "resolve"
        else:
            request_body["event_action"] = "trigger"

        # Set dedup key
        # We added "Promgen/" prefix to avoid collision with other systems
        request_body["dedup_key"] = str.format("Promgen/{}", util.fingerprint(data))

        # If we are triggering an alert, set extra fields, otherwise just send the resolve event
        if request_body["event_action"] == "resolve":
            return request_body

        # Set link to Promgen alert
        if "externalURL" in data:
            request_body["links"] = [
                {
                    "href": data["externalURL"],
                    "text": "View alert in Promgen",
                }
            ]

        # Initialize payload
        request_body.setdefault("payload", {})
        request_body["payload"]["source"] = "Promgen"

        # Set severity
        PAGERDUTY_ACCEPTED_SEVERITIES = {"info", "warning", "error", "critical"}
        severity = data["commonLabels"].get("severity")
        if severity in PAGERDUTY_ACCEPTED_SEVERITIES:
            request_body["payload"]["severity"] = severity
        elif severity and severity in settings.PAGERDUTY_SEVERITY_MAP:
            request_body["payload"]["severity"] = settings.PAGERDUTY_SEVERITY_MAP[severity]
        else:
            request_body["payload"]["severity"] = "error"

        # Set summary with a max length of 1024 characters
        # https://developer.pagerduty.com/docs/ZG9jOjExMDI5NTgx-send-an-alert-event
        if "summary" in data["commonAnnotations"]:
            request_body["payload"]["summary"] = data["commonAnnotations"]["summary"][:1024]
        else:
            request_body["payload"]["summary"] = data["commonLabels"]["alertname"][:1024]

        # Set custom details
        custom_details = {}
        custom_details["firing"] = "Labels:{}\nAnnotations:{} \n".format(
            NotificationPagerDuty.json_to_string(data["commonLabels"]),
            NotificationPagerDuty.json_to_string(data["commonAnnotations"]),
        )
        request_body["payload"]["custom_details"] = custom_details

        return request_body
