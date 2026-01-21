# Copyright (c) 2026 LY Corporation
# These sources are released under the terms of the MIT license: see LICENSE
import logging

import prometheus_client
from django.db import transaction

from promgen import models, util

logger = logging.getLogger(__name__)


def observe(name: str, label_values: dict, value: float):
    # Offload metric storage to a separate thread to avoid blocking
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        executor.submit(store_metric, name, label_values, value)


def store_metric(name: str, label_values: dict, value: float):
    try:
        metric = models.Metric.objects.get(name=name)
        if set(label_values.keys()) != set(metric.labels):
            raise ValueError("Label keys do not match metric.labels")

        values = ",".join(str(label_values[label]) for label in metric.labels)
        if metric.type == "counter":
            store_counter(metric, values, value)
        elif metric.type == "histogram":
            store_histogram(metric, values, value)
        else:
            raise NotImplementedError(f"Metric type {metric.type} not implemented")
    except Exception as e:
        logger.error(
            f"Failed to store metric {name} with labels {label_values} and value {value}: {e}"
        )
        raise


def store_counter(metric: models.Metric, label_values, value):
    if value < 0:
        raise ValueError("Counter value cannot be negative")

    with transaction.atomic():
        try:
            metric_sample = models.MetricSample.objects.select_for_update().get(
                metric=metric, labels=label_values
            )
            metric_sample.data["value"] += value
            metric_sample.save(update_fields=["data"])
        except models.MetricSample.DoesNotExist:
            # No existing sample matched, create a new one
            models.MetricSample.objects.create(
                metric=metric, labels=label_values, data={"value": value}
            )


def store_histogram(metric: models.Metric, label_values, value):
    with transaction.atomic():
        try:
            metric_sample = models.MetricSample.objects.select_for_update().get(
                metric=metric, labels=label_values
            )
            for bucket in metric_sample.data["buckets"]:
                bound, count = next(iter(bucket.items()))
                if value <= float(bound):
                    bucket[bound] += 1
            metric_sample.data["sum_value"] += value
            metric_sample.save(update_fields=["data"])

        except models.MetricSample.DoesNotExist:
            # No existing sample matched, create a new one
            buckets = []
            for bound in prometheus_client.Histogram.DEFAULT_BUCKETS:
                if value <= bound:
                    buckets.append({util.float_to_go_string(bound): 1})
                else:
                    buckets.append({util.float_to_go_string(bound): 0})
            models.MetricSample.objects.create(
                metric=metric,
                labels=label_values,
                data={"buckets": buckets, "sum_value": value},
            )
