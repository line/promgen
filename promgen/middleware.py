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
import uuid
from http import HTTPStatus
from threading import local

from django.contrib import messages
from django.db.models import prefetch_related_objects
from django.http import JsonResponse
from rest_framework import views, exceptions

from promgen import models, settings
from promgen.signals import trigger_write_config, trigger_write_rules, trigger_write_urls

logger = logging.getLogger(__name__)


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

        # Log all requests to our v2 API endpoints
        if settings.ENABLE_API_LOGGING and request.path.startswith("/rest/v2/"):
            try:
                # Generate a trace ID for each request
                trace_id = str(uuid.uuid4())
                request.trace_id = trace_id
                # Log the IP address of the request
                ip_address = request.META.get("REMOTE_ADDR")
                logger.info(f"[Trace ID: {trace_id}] IP Address: {ip_address}")
                # Log the user if authenticated
                if request.user.is_authenticated:
                    logger.info(f"[Trace ID: {trace_id}] User: {request.user.username}")
                # Log the request details
                logger.info(
                    f"[Trace ID: {request.trace_id}] Request: {request.method} {request.get_full_path()} - body size: {len(request.body) if request.body else 0} bytes"
                )
                if request.body and request.headers["Content-Type"] == "application/json":
                    # Only log first 512 characters of the request body to avoid flooding the logs
                    logger.info(
                        f"[Trace ID: {request.trace_id}] Request body: {json.dumps(json.loads(request.body))[:512]}"
                    )
            except Exception as e:
                logger.exception(
                    f"[Trace ID: {request.trace_id}] An error occurred when parsing request: {str(e)}"
                )

        response = self.get_response(request)

        # Log all responses to our v2 API endpoints
        if settings.ENABLE_API_LOGGING and request.path.startswith("/rest/v2/"):
            try:
                # Log the response details
                logger.info(
                    f"[Trace ID: {request.trace_id}] Response status: {response.status_code} - content size: {len(response.content)} bytes"
                )
            except Exception as e:
                logger.exception(
                    f"[Trace ID: {request.trace_id}] An error occurred when logging response: {str(e)}"
                )

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


def custom_exception_handler(exc, context):
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = views.exception_handler(exc, context)

    if response is None:
        # If an exception is raised that we don't handle, we will return a 500 error
        # with the exception message. This is useful for debugging in development
        if settings.DEBUG:
            return JsonResponse({"detail": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
        return exceptions.server_error(context["request"])

    return response
