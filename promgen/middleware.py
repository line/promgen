# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

"""
Promgen middleware

The middleware ensures three main things

1. We globally set request.site so that we can easily use it when searching for
   our global rule_set object

2. We store request.user globally so that we can retrieve it when logging users
   to our AuditLog

3. Since many different actions can trigger a write of the target.json or rules
files, we need to handle some deduplication. This is handled by using the django
caching system to set a key and then triggering the actual event from middleware
"""

import json
import logging
import socket
import uuid
from datetime import datetime
from threading import local

from django.contrib import messages
from django.contrib.admindocs.views import simplify_regex
from django.db.models import prefetch_related_objects

from promgen import metrics, models, settings, util
from promgen.signals import trigger_write_config, trigger_write_rules, trigger_write_urls

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler()
    logger.addHandler(handler)

_user = local()


class PromgenMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # This works the same as the django middleware
        # django.contrib.sites.middleware.CurrentSiteMiddleware
        # but ensures that it uses our proxy object so that test cases
        # properly find our rule_set object
        request.site = models.Site.objects.get_current()
        # Prefetch our rule_set as needed, since request.site is used on
        # many different pages
        prefetch_related_objects([request.site], "rule_set")

        # Get our logged in user to use with our audit logging plugin
        if request.user.is_authenticated:
            _user.value = request.user

        response = self.get_response(request)

        triggers = {
            "Config": trigger_write_config.send,
            "Rules": trigger_write_rules.send,
            "URLs": trigger_write_urls.send,
        }

        for msg, func in triggers.items():
            for receiver, status in func(self, request=request, force=True):
                if status is False:
                    messages.warning(request, "Error queueing %s " % msg)
        return response


def get_current_user():
    return getattr(_user, "value", None)


class PromgenMonitoringMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Log all requests to our v2 API endpoints
        if settings.V2_API_LOGGING_ENABLED and request.path.startswith("/rest/v2/"):
            # Generate a trace ID for each request
            request.trace_id = str(uuid.uuid4())
            try:
                truncated_body = (
                    util.truncate_json_fields(json.loads(request.body))
                    if request.body and request.headers["Content-Type"] == "application/json"
                    else None
                )
                logger.info(
                    f"[Trace ID: {request.trace_id}] "
                    f"User: {request.user.username if request.user.is_authenticated else None} - "
                    f"Request: {request.method} {request.get_full_path()} "
                    f"({len(request.body) if request.body else 0} bytes): "
                    f"{json.dumps(truncated_body)}"
                )
            except Exception as e:
                logger.exception(
                    f"[Trace ID: {request.trace_id}] An error occurred when parsing request: {e}"
                )

        started_time = datetime.now()
        response = self.get_response(request)
        finished_time = datetime.now()

        # Log all responses to v2 API endpoints
        if settings.V2_API_LOGGING_ENABLED and request.path.startswith("/rest/v2/"):
            try:
                logger.info(
                    f"[Trace ID: {request.trace_id}] "
                    f"Response status: {response.status_code} ({len(response.content)} bytes)"
                )
            except Exception as e:
                logger.exception(
                    f"[Trace ID: {request.trace_id}] An error occurred when logging response: {e}"
                )

        if request.resolver_match:
            endpoint = simplify_regex(request.resolver_match.route)
            method = request.method
            status_code = str(response.status_code)

            metrics.observe(
                "promgen_requests_total",
                label_values={
                    "endpoint": endpoint,
                    "hostname": socket.gethostname(),
                    "method": method,
                    "status_code": status_code,
                },
                value=1,
            )

            metrics.observe(
                name="promgen_requests_duration_seconds",
                label_values={
                    "endpoint": endpoint,
                    "hostname": socket.gethostname(),
                    "method": method,
                },
                value=(finished_time - started_time).total_seconds(),
            )

        return response
