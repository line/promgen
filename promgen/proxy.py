# Copyright (c) 2019 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import concurrent.futures
import json
import logging
from urllib.parse import urljoin

import requests
from django.http import HttpResponse, JsonResponse
from django.views.generic import View
from django.views.generic.base import TemplateView
from promgen import forms, models, prometheus, util
from requests.exceptions import HTTPError

logger = logging.getLogger(__name__)


def proxy_error(response):
    """
    Return a wrapped proxy error

    Taking a request.response object as input, return it slightly modified
    with an extra header for debugging so that we can see where the request
    failed
    """
    r = HttpResponse(
        response.content,
        content_type=response.headers["content-type"],
        status=response.status_code,
    )
    r.setdefault("X-PROMGEN-PROXY", response.url)
    return r


class PrometheusProxy(View):
    proxy_headers = {"HTTP_REFERER": "Referer"}

    @property
    def headers(self):
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
            for host in models.Shard.objects.filter(proxy=True):
                futures.append(
                    executor.submit(
                        util.get,
                        urljoin(host.url, request.get_full_path_info()),
                        headers=self.headers,
                    )
                )
            for future in concurrent.futures.as_completed(futures):
                yield future


class ProxyGraph(TemplateView):
    template_name = "promgen/graph.html"

    def get_context_data(self, **kwargs):
        context = super(ProxyGraph, self).get_context_data(**kwargs)
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
                return proxy_error(result)

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
                return proxy_error(result)

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
                return proxy_error(result)

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
                return proxy_error(result)

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
                return proxy_error(result)

        return JsonResponse(
            {"status": "success", "data": {"resultType": resultType, "result": data}}
        )


class ProxyAlerts(View):
    def get(self, request):
        try:
            url = urljoin(util.setting("alertmanager:url"), "/api/v1/alerts")
            response = util.get(url)
        except requests.exceptions.ConnectionError:
            logger.error("Error connecting to %s", url)
            return JsonResponse({})
        else:
            return HttpResponse(response.content, content_type="application/json")


class ProxySilences(View):
    def get(self, request):
        try:
            url = urljoin(util.setting("alertmanager:url"), "/api/v1/silences")
            response = util.get(url, params={"silenced": False})
        except requests.exceptions.ConnectionError:
            logger.error("Error connecting to %s", url)
            return JsonResponse({})
        else:
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
                status=422,
            )

        try:
            response = prometheus.silence(body.pop("labels"), **form.cleaned_data)
        except Exception as e:
            return JsonResponse(
                {"messages": [{"class": "alert alert-danger", "message": str(e)}]},
                status=400,
            )

        return HttpResponse(
            response.text, status=response.status_code, content_type="application/json"
        )


class ProxyDeleteSilence(View):
    def delete(self, request, silence_id):
        url = urljoin(
            util.setting("alertmanager:url"), "/api/v1/silence/%s" % silence_id
        )
        response = util.delete(url)
        return HttpResponse(
            response.text, status=response.status_code, content_type="application/json"
        )
