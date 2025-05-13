# Copyright (c) 2019 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import concurrent.futures
import json
import logging
from http import HTTPStatus
from urllib.parse import urljoin

import requests
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.views.generic import View
from django.views.generic.base import TemplateView
from guardian.shortcuts import get_objects_for_user
from requests.exceptions import HTTPError

from promgen import forms, models, prometheus, util

logger = logging.getLogger(__name__)


class PrometheusProxy(View):
    proxy_headers = {"HTTP_REFERER": "Referer"}

    @property
    def request_headers(self):
        # Loop through the headers from our request, and decide which ones
        # we should pass through upstream. Currently, our 'Referer' header is
        # the main one we are interested in, since this can help us debug which
        # grafana dashboard is responsible for the query.
        return {
            self.proxy_headers[k]: self.request.META[k]
            for k in self.proxy_headers
            if k in self.request.META
        }

    def proxy(self, request):
        futures = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            for shard in models.Shard.objects.filter(proxy=True):
                headers = self.request_headers
                if shard.authorization:
                    headers["Authorization"] = shard.authorization
                futures.append(
                    executor.submit(
                        util.get,
                        urljoin(shard.url, request.get_full_path_info()),
                        headers=headers,
                    )
                )
            yield from concurrent.futures.as_completed(futures)


class ProxyGraph(TemplateView):
    template_name = "promgen/graph.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["shard_list"] = models.Shard.objects.filter(proxy=True)
        for k, v in self.request.GET.items():
            _, k = k.split(".")
            context[k] = v
        return context


class ProxyLabels(PrometheusProxy):
    def get(self, request):
        data = set()
        for future in self.proxy(request):
            try:
                result = future.result()
                result.raise_for_status()
                _json = result.json()
                logger.debug("Appending data from %s", result.url)
                data.update(_json["data"])
            except HTTPError:
                logger.warning("Error with response")
                return util.proxy_error(result)

        return JsonResponse({"status": "success", "data": sorted(data)})


class ProxyLabelValues(PrometheusProxy):
    def get(self, request, label):
        data = set()
        for future in self.proxy(request):
            try:
                result = future.result()
                result.raise_for_status()
                _json = result.json()
                logger.debug("Appending data from %s", result.url)
                data.update(_json["data"])
            except HTTPError:
                logger.warning("Error with response")
                return util.proxy_error(result)

        return JsonResponse({"status": "success", "data": sorted(data)})


class ProxySeries(PrometheusProxy):
    def get(self, request):
        data = []
        for future in self.proxy(request):
            try:
                result = future.result()
                result.raise_for_status()
                _json = result.json()
                logger.debug("Appending data from %s", result.url)
                data += _json["data"]
            except HTTPError:
                logger.warning("Error with response")
                return util.proxy_error(result)

        return JsonResponse({"status": "success", "data": data})


class ProxyQueryRange(PrometheusProxy):
    def get(self, request):
        data = []
        resultType = None
        for future in self.proxy(request):
            try:
                result = future.result()
                result.raise_for_status()
                _json = result.json()
                logger.debug("Appending data from %s", result.url)
                data += _json["data"]["result"]
                resultType = _json["data"]["resultType"]
            except HTTPError:
                return util.proxy_error(result)

        return JsonResponse(
            {"status": "success", "data": {"resultType": resultType, "result": data}}
        )


class ProxyQuery(PrometheusProxy):
    def get(self, request):
        data = []
        resultType = None
        for future in self.proxy(request):
            try:
                result = future.result()
                result.raise_for_status()
                _json = result.json()
                logger.debug("Appending data from %s", result.url)
                data += _json["data"]["result"]
                resultType = _json["data"]["resultType"]
            except HTTPError:
                return util.proxy_error(result)

        return JsonResponse(
            {"status": "success", "data": {"resultType": resultType, "result": data}}
        )


class ProxyAlerts(View):
    def get(self, request):
        try:
            url = urljoin(util.setting("alertmanager:url"), "/api/v2/alerts")
            response = util.get(url)
        except requests.exceptions.ConnectionError:
            logger.error("Error connecting to %s", url)
            return JsonResponse({}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
        else:
            # Filter the alerts based on the user's permissions
            if not self.request.user.is_superuser:
                services = get_objects_for_user(
                    self.request.user,
                    ["service_admin", "service_editor", "service_viewer"],
                    any_perm=True,
                    use_groups=False,
                    accept_global_perms=False,
                    klass=models.Service,
                )

                projects = get_objects_for_user(
                    self.request.user,
                    ["project_admin", "project_editor", "project_viewer"],
                    any_perm=True,
                    use_groups=False,
                    accept_global_perms=False,
                    klass=models.Project,
                )
                projects = models.Project.objects.filter(
                    Q(pk__in=projects) | Q(service__in=services)
                )

                accessible_projects = projects.values_list("name", flat=True)
                accessible_services = services.values_list("name", flat=True)

                filtered_response = [
                    alert
                    for alert in response.json()
                    if alert.get("labels", {}).get("service") in accessible_services
                    or alert.get("labels", {}).get("project") in accessible_projects
                ]
                return HttpResponse(json.dumps(filtered_response), content_type="application/json")
            # If the user is a superuser, return all alerts
            return HttpResponse(response.content, content_type="application/json")


class ProxySilences(View):
    def get(self, request):
        try:
            url = urljoin(util.setting("alertmanager:url"), "/api/v2/silences")
            response = util.get(url, params={"silenced": False})
        except requests.exceptions.ConnectionError:
            logger.error("Error connecting to %s", url)
            return JsonResponse({}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
        else:
            # Filter the silences based on the user's permissions
            if not self.request.user.is_superuser:
                services = get_objects_for_user(
                    self.request.user,
                    ["service_admin", "service_editor", "service_viewer"],
                    any_perm=True,
                    use_groups=False,
                    accept_global_perms=False,
                    klass=models.Service,
                )

                projects = get_objects_for_user(
                    self.request.user,
                    ["project_admin", "project_editor", "project_viewer"],
                    any_perm=True,
                    use_groups=False,
                    accept_global_perms=False,
                    klass=models.Project,
                )
                projects = models.Project.objects.filter(
                    Q(pk__in=projects) | Q(service__in=services)
                )

                accessible_projects = projects.values_list("name", flat=True)
                accessible_services = services.values_list("name", flat=True)

                filtered_response = [
                    silence
                    for silence in response.json()
                    if any(
                        (
                            matcher.get("name") == "service"
                            and matcher.get("value") in accessible_services
                        )
                        or (
                            matcher.get("name") == "project"
                            and matcher.get("value") in accessible_projects
                        )
                        for matcher in silence.get("matchers", [])
                    )
                ]
                return HttpResponse(json.dumps(filtered_response), content_type="application/json")
            # If the user is a superuser, return all silences
            return HttpResponse(response.content, content_type="application/json")

    def post(self, request):
        body = json.loads(request.body.decode("utf-8"))
        body.setdefault("comment", "Silenced from Promgen")
        body.setdefault("createdBy", request.user.email)

        form = forms.SilenceForm(body)
        if not form.is_valid():
            return JsonResponse(
                {
                    "messages": [
                        {"class": "alert alert-warning", "message": m, "label": k}
                        for k in form.errors
                        for m in form.errors[k]
                    ]
                },
                status=HTTPStatus.UNPROCESSABLE_ENTITY,
            )

        # Check if the user has permission to silence the alert
        if not request.user.is_superuser:
            if "project" not in body["labels"] and "service" not in body["labels"]:
                return JsonResponse(
                    {
                        "messages": [
                            {
                                "class": "alert alert-warning",
                                "message": "You must specify either a project or service label",
                            }
                        ]
                    },
                    status=HTTPStatus.UNPROCESSABLE_ENTITY,
                )

            permission_denied_response = JsonResponse(
                {
                    "messages": [
                        {
                            "class": "alert alert-danger",
                            "message": "You do not have permission to silence this alert",
                        }
                    ]
                },
                status=HTTPStatus.FORBIDDEN,
            )
            if "project" in body["labels"]:
                project = models.Project.objects.get(name=body["labels"]["project"])
                if (
                    not request.user.has_perm("project_admin", project)
                    and not request.user.has_perm("project_editor", project)
                    and not request.user.has_perm("service_admin", project.service)
                    and not request.user.has_perm("service_editor", project.service)
                ):
                    return permission_denied_response
            elif "service" in body["labels"]:
                service = models.Service.objects.get(name=body["labels"]["service"])
                if not request.user.has_perm(
                    "service_admin", service
                ) and not request.user.has_perm("service_editor", service):
                    return permission_denied_response

        try:
            response = prometheus.silence(**form.cleaned_data)
        except requests.HTTPError as e:
            return JsonResponse(
                {
                    "messages": [
                        {"class": "alert alert-danger", "message": e.response.text},
                    ]
                },
                status=e.response.status_code,
            )
        except Exception as e:
            return JsonResponse(
                {"messages": [{"class": "alert alert-danger", "message": str(e)}]},
                status=HTTPStatus.UNPROCESSABLE_ENTITY,
            )

        return HttpResponse(
            response.text, status=response.status_code, content_type="application/json"
        )


class ProxyDeleteSilence(View):
    def delete(self, request, silence_id):
        url = urljoin(util.setting("alertmanager:url"), f"/api/v2/silence/{silence_id}")
        # First, check if the silence exists
        response = util.get(url)
        if response.status_code != 200:
            return HttpResponse(
                response.text, status=response.status_code, content_type="application/json"
            )

        # Check if the user has permission to delete the silence
        if not request.user.is_superuser:
            silence = response.json()
            project = None
            service = None
            for matcher in silence.get("matchers", []):
                if matcher.get("name") == "project":
                    project = matcher.get("value")
                if matcher.get("name") == "service":
                    service = matcher.get("value")
            if project is None and service is None:
                return JsonResponse(
                    {
                        "messages": [
                            {
                                "class": "alert alert-warning",
                                "message": "Silence must have either a project or service matcher",
                            }
                        ]
                    },
                    status=HTTPStatus.UNPROCESSABLE_ENTITY,
                )
            permission_denied_response = JsonResponse(
                {
                    "messages": [
                        {
                            "class": "alert alert-danger",
                            "message": "You do not have permission to delete this silence",
                        }
                    ]
                },
                status=HTTPStatus.FORBIDDEN,
            )
            if project:
                project = models.Project.objects.get(name=project)
                if (
                    not request.user.has_perm("project_admin", project)
                    and not request.user.has_perm("project_editor", project)
                    and not request.user.has_perm("service_admin", project.service)
                    and not request.user.has_perm("service_editor", project.service)
                ):
                    return permission_denied_response
            elif service:
                service = models.Service.objects.get(name=service)
                if not request.user.has_perm(
                    "service_admin", service
                ) and not request.user.has_perm("service_editor", service):
                    return permission_denied_response

        # Delete the silence
        response = util.delete(url)
        return HttpResponse(
            response.text, status=response.status_code, content_type="application/json"
        )
