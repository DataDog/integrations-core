# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from collections.abc import Callable
from pathlib import Path
from unittest.mock import patch

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.base.utils.discovery import Port, Service
from datadog_checks.krakend import KrakendCheck
from tests.helpers import get_metrics_from_metadata
from tests.types import InstanceBuilder


@pytest.fixture
def ready_check(check: KrakendCheck, dd_run_check: Callable, mock_http_response: Callable, aggregator: AggregatorStub):
    mocked_metrics_path = Path(__file__).parent / "fixtures" / "metrics.txt"
    mock_http_response(mocked_metrics_path.read_text())
    dd_run_check(check)
    dd_run_check(check)


def go_and_process_expected_metrics(go: bool, process: bool) -> list[tuple[str, bool]]:
    metadata_metrics = get_metrics_from_metadata()
    go_metrics = [(metric, go) for metric in metadata_metrics if metric.startswith("krakend.api.go")]

    process_metrics = [(metric, process) for metric in metadata_metrics if metric.startswith("krakend.api.process")]

    return go_metrics + process_metrics


@pytest.mark.parametrize(
    "go_metrics, process_metrics, expected_prefixes",
    [
        (True, True, ["go_", "process_"]),
        (False, True, ["process_"]),
        (True, False, ["go_"]),
        (False, False, []),
    ],
    ids=["process_and_go", "process_only", "go_only", "none"],
)
def test_check_filters_metrics_config(
    check: KrakendCheck,
    instance: InstanceBuilder,
    go_metrics: bool,
    process_metrics: bool,
    expected_prefixes: list[str],
):
    instance_config = instance(go_metrics=go_metrics, process_metrics=process_metrics)

    final_config = check.get_config_with_defaults(instance_config)

    prefixed_metrics: dict[str, list] = {expected_prefix: [] for expected_prefix in expected_prefixes}

    for expected_prefix in expected_prefixes:
        prefixed_metrics[expected_prefix].extend(
            [metric for metric in final_config["metrics"][0] if metric.startswith(expected_prefix)]
        )

    errors = []
    for expected_prefix in expected_prefixes:
        if len(prefixed_metrics[expected_prefix]) == 0:
            errors.append(f"No metrics with prefix {expected_prefix} found")

    assert len(errors) == 0, "\n".join(errors + [f"Metrics found: {prefixed_metrics}"])


def test_check_emits_metrics_as_in_metadata(ready_check: KrakendCheck, aggregator: AggregatorStub):
    metadata_metrics = get_metrics_from_metadata()
    aggregator.assert_metrics_using_metadata(
        metadata_metrics, check_submission_type=True, check_symmetric_inclusion=True
    )


@pytest.mark.parametrize(
    "check, expected_metrics",
    [
        ({"go_metrics": True, "process_metrics": True}, go_and_process_expected_metrics(True, True)),
        ({"go_metrics": False, "process_metrics": True}, go_and_process_expected_metrics(False, True)),
        ({"go_metrics": True, "process_metrics": False}, go_and_process_expected_metrics(True, False)),
        ({"go_metrics": False, "process_metrics": False}, go_and_process_expected_metrics(False, False)),
    ],
    indirect=["check"],
    ids=["process_and_go", "process_only", "go_only", "none"],
)
@pytest.mark.usefixtures("ready_check")
def test_check_filters_metrics(aggregator: AggregatorStub, expected_metrics: list[tuple[str, bool]]):
    errors = []
    for metric, is_emitted in expected_metrics:
        try:
            if not is_emitted:
                # Assert the metric is not emitted
                aggregator.assert_metric(metric, count=0)
            else:
                aggregator.assert_metric(metric)
        except AssertionError as e:
            errors.append(e)

    assert len(errors) == 0, "\n".join(str(e) for e in errors)


@pytest.mark.parametrize(
    "metric, tag",
    [
        ("krakend.api.http_client.request_timedout.count", "krakend.service_version:1.0.0"),
        ("krakend.api.http_client.request_timedout.count", "krakend.service_name:krakend-gateway"),
        ("krakend.api.go.info", "go_version:go1.24.4"),
    ],
    ids=["target_info_version", "target_info_service_name", "go_info_version"],
)
def test_labels_renaming(ready_check: KrakendCheck, aggregator: AggregatorStub, metric: str, tag: str):
    # All metrics should include the value from target_info with the appropriate tags renamed
    aggregator.assert_metric_has_tag(metric, tag)


def test_service_check_emitted(ready_check: KrakendCheck, aggregator: AggregatorStub):
    aggregator.assert_service_check("krakend.api.openmetrics.health", status=AgentCheck.OK)


def test_http_code_class_tag(ready_check: KrakendCheck, aggregator: AggregatorStub):
    aggregator.assert_metric_has_tag("krakend.api.http_client.duration.bucket", "code_class:5XX")


# ---------------------------------------------------------------------------
# discover() unit tests
# ---------------------------------------------------------------------------


def _service(*ports: int) -> Service:
    return Service(id="svc", host="h", ports=tuple(Port(number=p) for p in ports))


def test_discover_returns_url_for_first_matching_port():
    with patch("datadog_checks.base.utils.discovery.http_probe", side_effect=[True]) as probe:
        result = KrakendCheck.discover(_service(9090))
    assert result == [{"openmetrics_endpoint": "http://h:9090/metrics"}]
    probe.assert_called_once()


def test_discover_skips_non_matching_ports():
    with patch("datadog_checks.base.utils.discovery.http_probe", side_effect=[False, True]) as probe:
        result = KrakendCheck.discover(_service(8080, 9090))
    assert result == [{"openmetrics_endpoint": "http://h:9090/metrics"}]
    assert probe.call_count == 2


def test_discover_returns_none_when_no_port_matches():
    with patch("datadog_checks.base.utils.discovery.http_probe", side_effect=[False, False, False]) as probe:
        result = KrakendCheck.discover(_service(80, 8080, 9090))
    assert result is None
    assert probe.call_count == 3


def test_discover_returns_none_when_service_has_no_ports():
    with patch("datadog_checks.base.utils.discovery.http_probe") as probe:
        result = KrakendCheck.discover(_service())
    assert result is None
    probe.assert_not_called()
