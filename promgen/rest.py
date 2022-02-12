# Copyright (c) 2019 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE
import concurrent.futures
import requests
import logging

from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.serializers import ValidationError

from django.http import HttpResponse, JsonResponse
from django.views.generic import View

from promgen import filters, models, prometheus, renderers, serializers, tasks, util

logger = logging.getLogger(__name__)


class AlertReceiver(View):
    def post(self, request, *args, **kwargs):
        # Normally it would be more 'correct' to check our 'alert_blacklist' here and avoid
        # writing to the database, but to keep the alert ingestion queue as simple as possible
        # we will go ahead and write all alerts to the database and then filter out (delete)
        # when we run tasks.process_alert
        alert = models.Alert.objects.create(body=request.body.decode("utf-8"))
        tasks.process_alert.delay(alert.pk)
        return HttpResponse("OK", status=202)


class AllViewSet(viewsets.ViewSet):
    permission_classes = [permissions.AllowAny]

    @action(detail=False, methods=["get"], renderer_classes=[renderers.RuleRenderer])
    def rules(self, request):
        rules = models.Rule.objects.filter(enabled=True)
        return Response(
            serializers.AlertRuleSerializer(rules, many=True).data,
            headers={"Content-Disposition": "attachment; filename=alert.rule.yml"},
        )


class ShardViewSet(viewsets.ModelViewSet):
    queryset = models.Shard.objects.all()
    filterset_class = filters.ShardFilter
    serializer_class = serializers.ShardSerializer
    lookup_field = 'name'

    @action(detail=True, methods=['get'])
    def services(self, request, name):
        shard = self.get_object()
        return Response(
            serializers.ServiceSerializer(shard.service_set.all(), many=True).data
        )


class RuleMixin:
    @action(detail=True, methods=["get"], renderer_classes=[renderers.RuleRenderer])
    def rules(self, request, name):
        rules = models.Rule.objects.filter(obj=self.get_object())
        return Response(
            serializers.AlertRuleSerializer(rules, many=True).data,
            headers={"Content-Disposition": "attachment; filename=%s.rule.yml" % name},
        )


class NotifierMixin:
    @action(detail=True, methods=["get"])
    def notifiers(self, request, name):
        return Response(
            serializers.SenderSerializer(
                self.get_object().notifiers.all(), many=True
            ).data
        )


class ServiceViewSet(NotifierMixin, RuleMixin, viewsets.ModelViewSet):
    queryset = models.Service.objects.all()
    filterset_class = filters.ServiceFilter
    serializer_class = serializers.ServiceSerializer
    lookup_value_regex = '[^/]+'
    lookup_field = 'name'

    @action(detail=True, methods=['get'])
    def projects(self, request, name):
        service = self.get_object()
        return Response(
            serializers.ProjectSerializer(service.project_set.all(), many=True).data
        )

    @action(detail=True, methods=['get'])
    def targets(self, request, name):
        return HttpResponse(
            prometheus.render_config(service=self.get_object()),
            content_type='application/json',
        )


class ProjectViewSet(NotifierMixin, RuleMixin, viewsets.ModelViewSet):
    queryset = models.Project.objects.prefetch_related("service", "shard", "farm")
    filterset_class = filters.ProjectFilter
    serializer_class = serializers.ProjectSerializer
    lookup_value_regex = '[^/]+'
    lookup_field = 'name'

    @action(detail=True, methods=['get'])
    def targets(self, request, name):
        return HttpResponse(
            prometheus.render_config(project=self.get_object()),
            content_type='application/json',
        )

    @action(detail=True, methods=['post'])
    def scrape(self, request, name):
        serializer = serializers.ProjectScrapeSerializer(self.get_object(), data=request.data)

        def query():
            futures = []
            urls = serializer.get_scrape_urls()
            with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                for url in urls:
                    futures.append(
                        executor.submit(util.scrape, url)
                    )
                for future in concurrent.futures.as_completed(futures):
                    try:
                        result = future.result()
                        result.raise_for_status()
                        yield result.url, result.status_code
                    except requests.ConnectionError as ex:
                        logger.warning("Error connecting to server")
                        yield ex.request.url, "Error connecting to server"
                    except requests.RequestException as ex:
                        logger.warning("Error with response")
                        yield ex.request.url, str(ex)
                    except Exception as ex:
                        logger.exception("Unknown Exception %s" % ex)
                        yield "Unknown URL", "Unknown error"

        try:
            return JsonResponse(dict(query()))
        except ValidationError as e:
            return JsonResponse({'error': e.detail}, status=400)
        except Exception as e:
            logging.warning(e)
            return JsonResponse({"error": "Error with query %s" % e}, status=400)
