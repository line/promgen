# These sources are released under the terms of the MIT license: see LICENSE

import logging
from http import HTTPStatus

from django import forms

from promgen import util
from promgen.notification import NotificationBase

logger = logging.getLogger(__name__)


class FormSlack(forms.Form):
    value = forms.URLField(
        required=True,
        label="Slack Incoming Webhook URL",
    )
    alias = forms.CharField(
        required=False,
        help_text="Optional description to be displayed instead of the URL.",
    )


class NotificationSlack(NotificationBase):
    """
    Send messages to Slack via Incoming Webhook.

    An Incoming Webhook has to be configured for your workspace; you
    can set one up here:

    https://my.slack.com/services/new/incoming-webhook/

    A fitting Prometheus icon can be selected from here:

    https://github.com/quintessence/slack-icons
    """

    form = FormSlack

    def _send(self, url, data):
        kwargs = {}
        proxy = self.config("proxies", default=None)
        if proxy:
            kwargs["proxies"] = {
                "http": proxy,
                "https": proxy,
            }

        if data["status"] == "resolved":
            message = self.render("promgen/sender/slack.resolved.txt", data)
        else:
            message = self.render("promgen/sender/slack.body.txt", data)

        json = {
            "text": message,
        }

        util.post_with_retry(
            url,
            json=json,
            retry_codes=(
                HTTPStatus.GATEWAY_TIMEOUT,
                HTTPStatus.TOO_MANY_REQUESTS,
                HTTPStatus.SERVICE_UNAVAILABLE,
            ),
            **kwargs,
        ).raise_for_status()
