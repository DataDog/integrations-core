# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from collections import namedtuple

import mock
import pytest

from datadog_checks.kube_apiserver_metrics import KubeAPIServerMetricsCheck

from .common import HERE

# Constants
CHECK_NAME = "kube_apiserver"


@pytest.fixture()
def mock_metrics():
    f_name = os.path.join(HERE, "fixtures", "metrics_slis_1.27.3.txt")
    with open(f_name, "r") as f:
        text_data = f.read()
    with mock.patch(
        "requests.get",
        return_value=mock.MagicMock(
            status_code=200,
            iter_lines=lambda **kwargs: text_data.split("\n"),
            headers={"Content-Type": "text/plain"},
        ),
    ):
        yield


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

    def assert_metric(name, **kwargs):
        # Wrapper to keep assertions < 120 chars
        aggregator.assert_metric("{}.{}".format(CHECK_NAME, name), **kwargs)

    # Check that no metrics with `name` tag come through
    assert_metric(
        "slis.kubernetes_healthcheck",
        count=0,
        metric_type=aggregator.GAUGE,
        tags=["name:autoregister-completion"],
    )
    assert_metric(
        "slis.kubernetes_healthchecks_total",
        metric_type=aggregator.MONOTONIC_COUNT,
        count=0,
        tags=["name:autoregister-completion", "status:error"],
    )


def test_check_metrics_slis_filter_by_type(aggregator, mock_metrics, instance):
    c = KubeAPIServerMetricsCheck(CHECK_NAME, {}, [instance])
    c.check(instance)

    def assert_metric(name, **kwargs):
        # Wrapper to keep assertions < 120 chars
        aggregator.assert_metric("{}.{}".format(CHECK_NAME, name), **kwargs)

    # Check that metrics with type other than `healthz` are filtered out
    assert_metric(
        "slis.kubernetes_healthcheck",
        count=0,
        metric_type=aggregator.GAUGE,
        tags=["sli_name:autoregister-completion", "type:readyz"],
    )

    assert_metric(
        "slis.kubernetes_healthchecks_total",
        metric_type=aggregator.MONOTONIC_COUNT,
        count=0,
        tags=["sli_name:autoregister-completion", "status:error", "type:readyz"],
    )


def test_detect_sli_endpoint(mock_metrics, instance):
    c = KubeAPIServerMetricsCheck(CHECK_NAME, {}, [instance])
    assert c._slis_available is True


def test_detect_sli_endpoint_404(instance, mock_http_response):
    mock_http_response(status_code=404)
    c = KubeAPIServerMetricsCheck(CHECK_NAME, {}, [instance])
    assert c._slis_available is False


def test_detect_sli_endpoint_403(instance, mock_http_response):
    mock_http_response(status_code=403)
    c = KubeAPIServerMetricsCheck(CHECK_NAME, {}, [instance])
    assert c._slis_available is False
