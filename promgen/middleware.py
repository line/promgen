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
from rest_framework import exceptions, views

from promgen import models, settings
from promgen.signals import trigger_write_config, trigger_write_rules, trigger_write_urls

logger = logging.getLogger(__name__)


_user = local()


class PromgenMiddleware:
    ACCESS_LOG_FIELD_LIMITS = {
        "body": 8192,
        "description": 512,
        "clause": 8192,
    }

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
                        f"[Trace ID: {request.trace_id}] Request body: {self.truncate_json_fields(json.loads(request.body), self.ACCESS_LOG_FIELD_LIMITS)}"
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

    @staticmethod
    def truncate_json_fields(data, field_limits, default_limits=128):
        """
        Recursively truncate fields in a JSON object based on a given field-length mapping.

        Args:
            data (dict): The JSON object to process.
            field_limits (dict): A mapping of field names to their maximum lengths.
            default_limits (int): Default maximum length for fields not specified in field_limits.

        Returns:
            dict: A new JSON object with truncated fields.
        """
        truncated_data = {}
        for field, value in data.items():
            if isinstance(value, dict):
                # Recursively process nested dictionaries
                truncated_data[field] = PromgenMiddleware.truncate_json_fields(value, field_limits)
            elif field in field_limits and isinstance(value, str):
                truncated_data[field] = value[: field_limits[field]] + (
                    "..." if len(value) > field_limits[field] else ""
                )
            elif isinstance(value, str):
                truncated_data[field] = value[:default_limits] + (
                    "..." if len(value) > default_limits else ""
                )
            else:
                truncated_data[field] = value
        return truncated_data


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
