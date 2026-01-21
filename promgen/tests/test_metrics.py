# Copyright (c) 2026 LY Corporation
# These sources are released under the terms of the MIT license: see LICENSE


from promgen import metrics, models
from promgen.tests import PromgenTest


class MetricTest(PromgenTest):
    def setUp(self):
        models.Metric.objects.create(
            name="test_counter",
            type="counter",
            labels=["method", "status"],
        )
        models.Metric.objects.create(
            name="test_histogram",
            type="histogram",
            labels=["endpoint"],
        )

    def test_metric_counter(self):
        metric = models.Metric.objects.get(name="test_counter")
        self.assertEqual(metric.type, "counter")

        # Store a counter metric
        metrics.store_metric(
            name="test_counter",
            label_values={"method": "GET", "status": "200"},
            value=1,
        )
        metrics.store_metric(
            name="test_counter",
            label_values={"method": "POST", "status": "202"},
            value=2,
        )

        sample = models.MetricSample.objects.get(metric=metric, labels="GET,200")
        self.assertEqual(sample.data["value"], 1)
        sample = models.MetricSample.objects.get(metric=metric, labels="POST,202")
        self.assertEqual(sample.data["value"], 2)

        # Store again to check increment
        metrics.store_metric(
            name="test_counter",
            label_values={"status": "200", "method": "GET"},
            value=1,
        )

        sample = models.MetricSample.objects.get(metric=metric, labels="GET,200")
        self.assertEqual(sample.data["value"], 2)

    def test_metric_histogram(self):
        metric = models.Metric.objects.get(name="test_histogram")
        self.assertEqual(metric.type, "histogram")

        # Store a histogram metric
        metrics.store_metric(
            name="test_histogram",
            label_values={"endpoint": "/api/v1/resource"},
            value=0.3,
        )
        metrics.store_metric(
            name="test_histogram",
            label_values={"endpoint": "/api/v1/resource"},
            value=1.2,
        )

        sample = models.MetricSample.objects.get(metric=metric, labels="/api/v1/resource")
        buckets = sample.data["buckets"]

        # Check bucket counts
        for bucket in buckets:
            for bound, count in bucket.items():
                if 0.5 <= float(bound) < 2.5:
                    self.assertEqual(count, 1)
                elif float(bound) >= 2.5:
                    self.assertEqual(count, 2)
                else:
                    self.assertEqual(count, 0)
        # Check sum value
        self.assertEqual(sample.data["sum_value"], 1.5)

    def test_metric_label_mismatch(self):
        with self.assertRaises(ValueError):
            metrics.store_metric(
                name="test_counter",
                label_values={"method": "GET"},
                value=1,
            )
