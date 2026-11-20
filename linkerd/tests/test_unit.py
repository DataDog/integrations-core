# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest
import requests_mock

from datadog_checks.linkerd import LinkerdCheck
from datadog_checks.linkerd.check import LinkerdCheckV2
from datadog_checks.linkerd.metrics import construct_metrics_config

from .common import HERE, MOCK_INSTANCE, MOCK_INSTANCE_NEW

pytestmark = pytest.mark.unit


def get_fixture_path(filename):
    return os.path.join(HERE, "fixtures", filename)


def get_response(filename):
    with open(get_fixture_path(filename), "r") as f:
        return f.read()


def test_construct_metrics_config_strips_total_suffix():
    out = construct_metrics_config({"linkerd_foo_total": "foo.total"}, {})
    assert out == [{"linkerd_foo": {"name": "foo"}}]


def test_construct_metrics_config_passes_through_when_no_suffix():
    out = construct_metrics_config({"linkerd_bar": "bar"}, {})
    assert out == [{"linkerd_bar": {"name": "bar"}}]


def test_v2_default_metric_limit_is_zero():
    assert LinkerdCheckV2.DEFAULT_METRIC_LIMIT == 0


def test_v2_check_reports_health_ok_on_success(aggregator, dd_run_check, mock_http_response):
    mock_http_response(file_path=get_fixture_path("linkerd_v2.txt"))
    check = LinkerdCheckV2("linkerd", {}, [MOCK_INSTANCE_NEW])
    dd_run_check(check)
    aggregator.assert_metric("linkerd.openmetrics.health", value=0, count=1)


def test_v2_check_reports_health_critical_and_reraises_on_failure(aggregator, dd_run_check):
    check = LinkerdCheckV2("linkerd", {}, [MOCK_INSTANCE_NEW])
    with requests_mock.Mocker() as metric_request:
        metric_request.get("http://fake.tld/prometheus", exc=Exception("boom"))
        with pytest.raises(Exception):
            dd_run_check(check)
    aggregator.assert_metric("linkerd.openmetrics.health", value=1, count=1)


def test_legacy_default_metric_limit_is_zero():
    assert LinkerdCheck.DEFAULT_METRIC_LIMIT == 0


def test_legacy_new_uses_first_instance_for_routing():
    check = LinkerdCheck(
        "linkerd",
        {},
        [
            {"openmetrics_endpoint": "http://fake.tld/prometheus"},
            {"prometheus_url": "http://fake.tld/prometheus2"},
        ],
    )
    assert isinstance(check, LinkerdCheckV2)


def test_legacy_process_reports_health_ok_on_success(aggregator, dd_run_check):
    check = LinkerdCheck("linkerd", {}, [MOCK_INSTANCE])
    with requests_mock.Mocker() as metric_request:
        metric_request.get("http://fake.tld/prometheus", text=get_response("linkerd.txt"))
        dd_run_check(check)
    aggregator.assert_metric("linkerd.prometheus.health", value=0, count=1)


def test_legacy_process_reports_health_critical_and_reraises_on_failure(aggregator, dd_run_check):
    check = LinkerdCheck("linkerd", {}, [MOCK_INSTANCE])
    with requests_mock.Mocker() as metric_request:
        metric_request.get("http://fake.tld/prometheus", exc=Exception("boom"))
        with pytest.raises(Exception):
            dd_run_check(check)
    aggregator.assert_metric("linkerd.prometheus.health", value=1, count=1)
