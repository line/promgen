# Copyright (c) 2019 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import concurrent.futures
import logging

from django.http import JsonResponse
from django.views.generic import View
from django.views.generic.base import TemplateView
from promgen import models, util
from requests.exceptions import HTTPError

logger = logging.getLogger(__name__)


class PrometheusProxy(View):
    # Map Django request headers to our sub-request headers
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


class ProxyGraph(TemplateView):
    template_name = "promgen/graph.html"

    def get_context_data(self, **kwargs):
        context = super(ProxyGraph, self).get_context_data(**kwargs)
        context["shard_list"] = models.Shard.objects.filter(proxy=True)
        for k, v in self.request.GET.items():
            _, k = k.split(".")
            context[k] = v
        return context


class ProxyLabel(PrometheusProxy):
    def get(self, request, label):
        data = set()
        futures = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            for host in models.Shard.objects.filter(proxy=True):
                futures.append(
                    executor.submit(
                        util.get,
                        "{}/api/v1/label/{}/values".format(host.url, label),
                        headers=self.headers,
                    )
                )
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    # Need to try to decode the json BEFORE we raise_for_status
                    # so that we can pass back the error message from Prometheus
                    _json = result.json()
                    result.raise_for_status()
                    logger.debug("Appending data from %s", result.request.url)
                    data.update(_json["data"])
                except HTTPError:
                    logger.warning("Error with response")
                    _json["promgen_proxy_request"] = result.request.url
                    return JsonResponse(_json, status=result.status_code)

        return JsonResponse({"status": "success", "data": sorted(data)})


class ProxySeries(PrometheusProxy):
    def get(self, request):
        data = []
        futures = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            for host in models.Shard.objects.filter(proxy=True):
                futures.append(
                    executor.submit(
                        util.get,
                        "{}/api/v1/series?{}".format(
                            host.url, request.META["QUERY_STRING"]
                        ),
                        headers=self.headers,
                    )
                )
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    # Need to try to decode the json BEFORE we raise_for_status
                    # so that we can pass back the error message from Prometheus
                    _json = result.json()
                    result.raise_for_status()
                    logger.debug("Appending data from %s", result.request.url)
                    data += _json["data"]
                except HTTPError:
                    logger.warning("Error with response")
                    _json["promgen_proxy_request"] = result.request.url
                    return JsonResponse(_json, status=result.status_code)

        return JsonResponse({"status": "success", "data": data})


class ProxyQueryRange(PrometheusProxy):
    def get(self, request):
        data = []
        futures = []
        resultType = None
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            for host in models.Shard.objects.filter(proxy=True):
                futures.append(
                    executor.submit(
                        util.get,
                        "{}/api/v1/query_range?{}".format(
                            host.url, request.META["QUERY_STRING"]
                        ),
                        headers=self.headers,
                    )
                )
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    # Need to try to decode the json BEFORE we raise_for_status
                    # so that we can pass back the error message from Prometheus
                    _json = result.json()
                    result.raise_for_status()
                    logger.debug("Appending data from %s", result.request.url)
                    data += _json["data"]["result"]
                    resultType = _json["data"]["resultType"]
                except HTTPError:
                    logger.warning("Error with response")
                    _json["promgen_proxy_request"] = result.request.url
                    return JsonResponse(_json, status=result.status_code)

        return JsonResponse(
            {"status": "success", "data": {"resultType": resultType, "result": data}}
        )


class ProxyQuery(PrometheusProxy):
    def get(self, request):
        data = []
        futures = []
        resultType = None
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            for host in models.Shard.objects.filter(proxy=True):
                futures.append(
                    executor.submit(
                        util.get,
                        "{}/api/v1/query?{}".format(
                            host.url, request.META["QUERY_STRING"]
                        ),
                        headers=self.headers,
                    )
                )
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    # Need to try to decode the json BEFORE we raise_for_status
                    # so that we can pass back the error message from Prometheus
                    _json = result.json()
                    result.raise_for_status()
                    logger.debug("Appending data from %s", result.request.url)
                    data += _json["data"]["result"]
                    resultType = _json["data"]["resultType"]
                except HTTPError:
                    logger.warning("Error with response")
                    _json["promgen_proxy_request"] = result.request.url
                    return JsonResponse(_json, status=result.status_code)

        return JsonResponse(
            {"status": "success", "data": {"resultType": resultType, "result": data}}
        )
