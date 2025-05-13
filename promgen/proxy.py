# Copyright (c) 2019 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import concurrent.futures
import json
import logging
from http import HTTPStatus
from urllib.parse import urljoin

import requests
from django.http import HttpResponse, JsonResponse
from django.utils.translation import gettext as _
from django.views.generic import View
from django.views.generic.base import TemplateView
from requests.exceptions import HTTPError
from rest_framework import permissions
from rest_framework.views import APIView

from promgen import forms, models, prometheus, serializers, util
from promgen import permissions as promgen_permissions

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
                services = promgen_permissions.get_accessible_services_for_user(self.request.user)
                projects = promgen_permissions.get_accessible_projects_for_user(self.request.user)

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


def get_affected_obj_by_matchers(matchers):
    def get_queryset_for_matcher(matcher, klass):
        if matcher["isEqual"] and matcher["isRegex"]:  # =~
            return klass.objects.filter(name__regex="^(?:" + matcher["value"] + ")$")
        elif matcher["isEqual"]:  # =
            return klass.objects.filter(name=matcher["value"])
        elif matcher["isRegex"]:  # !~
            return klass.objects.exclude(name__regex="^(?:" + matcher["value"] + ")$")
        else:  # !=
            return klass.objects.exclude(name=matcher["value"])

    affected_projects = models.Project.objects.all()
    affected_services = models.Service.objects.all()
    has_project_matcher = has_service_matcher = False

    for matcher in matchers:
        if matcher["name"] == "project":
            has_project_matcher = True
            qs = get_queryset_for_matcher(matcher, models.Project)
            affected_projects = affected_projects.filter(id__in=qs.values_list("id", flat=True))
        elif matcher["name"] == "service":
            has_service_matcher = True
            qs = get_queryset_for_matcher(matcher, models.Service)
            affected_services = affected_services.filter(id__in=qs.values_list("id", flat=True))

    if not has_project_matcher:
        affected_projects = models.Project.objects.none()
    if not has_service_matcher:
        affected_services = models.Service.objects.none()

    return affected_projects, affected_services


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
                accessible_projects = promgen_permissions.get_accessible_projects_for_user(
                    self.request.user
                )
                accessible_services = promgen_permissions.get_accessible_services_for_user(
                    self.request.user
                )

                filtered_silences = []
                for silence in response.json():
                    affected_projects, affected_services = get_affected_obj_by_matchers(
                        silence.get("matchers", [])
                    )
                    if (
                        affected_projects.filter(
                            id__in=accessible_projects.values_list("id", flat=True)
                        ).exists()
                        or affected_services.filter(
                            id__in=accessible_services.values_list("id", flat=True)
                        ).exists()
                    ):
                        filtered_silences.append(silence)

                return HttpResponse(json.dumps(filtered_silences), content_type="application/json")

            return HttpResponse(response.content, content_type="application/json")

    def post(self, request):
        body = json.loads(request.body.decode("utf-8"))
        body.setdefault("comment", "Silenced from Promgen")
        body.setdefault("createdBy", request.user.username)

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
                                "message": _("You must specify either a project or service label."),
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
                            "message": _("You do not have permission to silence this alert."),
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


def get_uneditable_obj_by_silence_matchers(matchers, user):
    affected_projects, affected_services = get_affected_obj_by_matchers(matchers)

    uneditable_projects = models.Project.objects.none()
    uneditable_services = models.Service.objects.none()

    if affected_projects.exists():
        editable_projects = promgen_permissions.get_editable_projects_for_user(user)
        uneditable_projects = affected_projects.exclude(
            id__in=editable_projects.values_list("id", flat=True)
        )

    # If there are any affected projects, the silence is already related to some projects.
    # Therefore, checking permissions on projects is sufficient.
    if not affected_projects.exists() and affected_services.exists():
        editable_services = promgen_permissions.get_editable_services_for_user(user)
        uneditable_services = affected_services.exclude(
            id__in=editable_services.values_list("id", flat=True)
        )

    return uneditable_projects, uneditable_services


class ProxySilencesV2(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = serializers.SilenceSerializer(
            data={**request.data, "createdBy": request.user.username}
        )
        if not serializer.is_valid():
            return JsonResponse(
                {
                    "messages": [
                        {"class": "alert alert-warning", "message": _(m), "label": k}
                        for k in serializer.errors
                        for m in serializer.errors[k]
                    ]
                },
                status=HTTPStatus.UNPROCESSABLE_ENTITY,
            )

        # Check if the user has permission to silence the alert
        if not request.user.is_superuser:
            uneditable_projects, uneditable_services = get_uneditable_obj_by_silence_matchers(
                serializer.data["matchers"], request.user
            )
            messages = []
            for objs, label in [
                (uneditable_projects, "projects"),
                (uneditable_services, "services"),
            ]:
                if objs.exists():
                    count = objs.count()
                    if count <= 20:
                        names = ", ".join(objs.values_list("name", flat=True))
                        messages.append(
                            {
                                "class": "alert alert-warning",
                                "message": _(
                                    "You do not have permission to silence alerts for "
                                    "the following {label}: {names}."
                                ).format(label=label, names=names),
                            }
                        )
                    else:
                        messages.append(
                            {
                                "class": "alert alert-warning",
                                "message": _(
                                    "You do not have permission to silence alerts for "
                                    "many ({count}) {label}."
                                ).format(count=count, label=label),
                            }
                        )
            if messages:
                return JsonResponse(
                    {"messages": messages},
                    status=HTTPStatus.FORBIDDEN,
                )

        try:
            response = prometheus.silence(labels=None, **serializer.data)
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
            uneditable_projects, uneditable_services = get_uneditable_obj_by_silence_matchers(
                silence.get("matchers", []), request.user
            )
            messages = []
            for objs, label in [
                (uneditable_projects, "projects"),
                (uneditable_services, "services"),
            ]:
                if objs.exists():
                    count = objs.count()
                    if count <= 20:
                        names = ", ".join(objs.values_list("name", flat=True))
                        messages.append(
                            {
                                "class": "alert alert-warning",
                                "message": _(
                                    "You do not have permission to expire the silence that matches "
                                    "the following {label}: {names}."
                                ).format(label=label, names=names),
                            }
                        )
                    else:
                        messages.append(
                            {
                                "class": "alert alert-warning",
                                "message": _(
                                    "You do not have permission to expire the silence that matches "
                                    "many ({count}) {label}."
                                ).format(count=count, label=label),
                            }
                        )
            if messages:
                return JsonResponse(
                    {"messages": messages},
                    status=HTTPStatus.FORBIDDEN,
                )

        # Delete the silence
        response = util.delete(url)
        return HttpResponse(
            response.text, status=response.status_code, content_type="application/json"
        )
