# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Any, Callable, Dict  # noqa: F401

import pytest

from datadog_checks.base import AgentCheck  # noqa: F401
from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.kubevirt_handler import KubevirtHandlerCheck

from .conftest import mock_http_responses

base_tags = [
    "pod_name:virt-handler-some-id",
    "kube_namespace:kubevirt",
    "kube_cluster_name:test-cluster",
]


def test_check(dd_run_check, aggregator, instance, mocker):
    # type: (Callable[[AgentCheck, bool], None], AggregatorStub, Dict[str, Any]) -> None
    mocker.patch("requests.get", wraps=mock_http_responses)
    check = KubevirtHandlerCheck("kubevirt_handler", {}, [instance])
    dd_run_check(check)

    aggregator.assert_metric(
        "kubevirt_handler.can_connect",
        1,
        tags=["endpoint:https://127.0.0.1:8443/healthz", *base_tags],
    )

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_logs_warning_when_healthz_endpoint_is_missing(dd_run_check, aggregator, instance, caplog):
    # type: (Callable[[AgentCheck, bool], None], AggregatorStub, Dict[str, Any]) -> None
    del instance["kubevirt_handler_healthz_endpoint"]
    check = KubevirtHandlerCheck("kubevirt_handler", {}, [instance])
    dd_run_check(check)
    assert (
        "Skipping health check. Please provide a `kubevirt_handler_healthz_endpoint` to ensure the health of the KubeVirt Handler."  # noqa: E501
        in caplog.text
        and "WARNING" in caplog.text
    )


def test_emits_can_connect_one_when_service_is_up(dd_run_check, aggregator, instance, mocker):
    # type: (Callable[[AgentCheck, bool], None], AggregatorStub, Dict[str, Any]) -> None
    mocker.patch("requests.get", wraps=mock_http_responses)
    check = KubevirtHandlerCheck("kubevirt_handler", {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric(
        "kubevirt_handler.can_connect",
        1,
        tags=["endpoint:https://127.0.0.1:8443/healthz", *base_tags],
    )


def test_emits_can_connect_zero_when_service_is_down(dd_run_check, aggregator, instance):
    # type: (Callable[[AgentCheck, bool], None], AggregatorStub, Dict[str, Any]) -> None
    check = KubevirtHandlerCheck("kubevirt_handler", {}, [instance])
    with pytest.raises(Exception):
        dd_run_check(check)

    aggregator.assert_metric(
        "kubevirt_handler.can_connect",
        0,
        tags=["endpoint:https://127.0.0.1:8443/healthz", *base_tags],
    )
