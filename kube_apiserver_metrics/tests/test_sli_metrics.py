# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from collections import namedtuple

import pytest

from datadog_checks.kube_apiserver_metrics import KubeAPIServerMetricsCheck

from .common import make_mock_metrics

# Constants
CHECK_NAME = "kube_apiserver"


@pytest.fixture()
def mock_metrics(mock_openmetrics_http):
    return make_mock_metrics(mock_openmetrics_http, 'metrics_slis_1.27.3.txt')


def test_check_metrics_slis(aggregator, mock_metrics, instance):
    c = KubeAPIServerMetricsCheck(CHECK_NAME, {}, [instance])
    c.check(instance)
    SLIMetric = namedtuple("SLIMetric", ["name", "value", "tags"])

    expected_metrics = [
        SLIMetric("slis.kubernetes_healthcheck", 1, ["sli_name:autoregister-completion"]),
        SLIMetric("slis.kubernetes_healthcheck", 1, ["sli_name:etcd"]),
        SLIMetric("slis.kubernetes_healthcheck", 1, ["sli_name:log"]),
        SLIMetric("slis.kubernetes_healthcheck", 1, ["sli_name:ping"]),
        SLIMetric("slis.kubernetes_healthcheck", 1, ["sli_name:poststarthook/aggregator-reload-proxy-client-cert"]),
        SLIMetric("slis.kubernetes_healthcheck", 1, ["sli_name:poststarthook/apiservice-discovery-controller"]),
        SLIMetric("slis.kubernetes_healthchecks_total", 1, ["sli_name:autoregister-completion", "status:error"]),
        SLIMetric("slis.kubernetes_healthchecks_total", 4, ["sli_name:autoregister-completion", "status:success"]),
        SLIMetric("slis.kubernetes_healthchecks_total", 5, ["sli_name:etcd", "status:success"]),
        SLIMetric("slis.kubernetes_healthchecks_total", 5, ["sli_name:log", "status:success"]),
        SLIMetric("slis.kubernetes_healthchecks_total", 5, ["sli_name:ping", "status:success"]),
        SLIMetric(
            "slis.kubernetes_healthchecks_total",
            5,
            ["sli_name:poststarthook/aggregator-reload-proxy-client-cert", "status:success"],
        ),
        SLIMetric(
            "slis.kubernetes_healthchecks_total",
            5,
            ["sli_name:poststarthook/apiservice-discovery-controller", "status:success"],
        ),
    ]
    for metric in expected_metrics:
        aggregator.assert_metric("{}.{}".format(CHECK_NAME, metric.name), value=metric.value, tags=metric.tags)

    aggregator.assert_all_metrics_covered()


def test_check_metrics_slis_transform(aggregator, mock_metrics, instance):
    c = KubeAPIServerMetricsCheck(CHECK_NAME, {}, [instance])
    c.check(instance)

    SLIMetric = namedtuple("SLIMetric", ["name", "count", "tags"])

    expected_metrics = [
        SLIMetric("slis.kubernetes_healthcheck", 0, ["name:autoregister-completion"]),
        SLIMetric("slis.kubernetes_healthchecks_total", 0, ["name:autoregister-completion", "status:error"]),
    ]

    for metric in expected_metrics:
        aggregator.assert_metric("{}.{}".format(CHECK_NAME, metric.name), count=metric.count, tags=metric.tags)


def test_check_metrics_slis_filter_by_type(aggregator, mock_metrics, instance):
    c = KubeAPIServerMetricsCheck(CHECK_NAME, {}, [instance])
    c.check(instance)

    SLIMetric = namedtuple("SLIMetric", ["name", "count", "tags"])

    expected_metrics = [
        SLIMetric("slis.kubernetes_healthcheck", 0, ["sli_name:autoregister-completion", "type:readyz"]),
        SLIMetric(
            "slis.kubernetes_healthchecks_total", 0, ["sli_name:autoregister-completion", "status:error", "type:readyz"]
        ),
    ]

    for metric in expected_metrics:
        aggregator.assert_metric("{}.{}".format(CHECK_NAME, metric.name), count=metric.count, tags=metric.tags)


def test_detect_sli_endpoint(aggregator, mock_metrics, instance):
    c = KubeAPIServerMetricsCheck(CHECK_NAME, {}, [instance])
    c.check(instance)
    SLIMetric = namedtuple("SLIMetric", ["name", "count"])

    expected_metrics = [
        SLIMetric("slis.kubernetes_healthcheck", 6),
        SLIMetric("slis.kubernetes_healthchecks_total", 7),
    ]
    for metric in expected_metrics:
        aggregator.assert_metric("{}.{}".format(CHECK_NAME, metric.name), count=metric.count)
    aggregator.assert_all_metrics_covered()


def test_detect_sli_endpoint_404(aggregator, instance, mock_http_response):
    mock_http_response(status_code=404)
    c = KubeAPIServerMetricsCheck(CHECK_NAME, {}, [instance])
    mock_http_response(status_code=200)
    c.check(instance)
    SLIMetric = namedtuple("SLIMetric", ["name", "count"])

    expected_metrics = [
        SLIMetric("slis.kubernetes_healthcheck", 0),
        SLIMetric("slis.kubernetes_healthchecks_total", 0),
    ]
    for metric in expected_metrics:
        aggregator.assert_metric("{}.{}".format(CHECK_NAME, metric.name), count=metric.count)


def test_detect_sli_endpoint_403(aggregator, instance, mock_http_response):
    mock_http_response(status_code=403)
    c = KubeAPIServerMetricsCheck(CHECK_NAME, {}, [instance])
    mock_http_response(status_code=200)
    c.check(instance)
    SLIMetric = namedtuple("SLIMetric", ["name", "count"])

    expected_metrics = [
        SLIMetric("slis.kubernetes_healthcheck", 0),
        SLIMetric("slis.kubernetes_healthchecks_total", 0),
    ]
    for metric in expected_metrics:
        aggregator.assert_metric("{}.{}".format(CHECK_NAME, metric.name), count=metric.count)
