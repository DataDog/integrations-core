# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from unittest.mock import MagicMock  # noqa: F401

import pytest

from datadog_checks.base import AgentCheck  # noqa: F401
from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.kubevirt_api import KubevirtApiCheck

from .conftest import mock_http_responses
from .mock_response import GET_PODS_RESPONSE_VIRT_API_POD, GET_VMIS_RESPONSE, GET_VMS_RESPONSE

pytestmark = [pytest.mark.unit]


def test_check(dd_run_check, aggregator, instance, mocker):
    mocker.patch("requests.get", wraps=mock_http_responses)

    check = KubevirtApiCheck("kubevirt_api", {}, [instance])

    check._setup = lambda: None
    check.kube_client = MagicMock()
    check.kube_client.get_pods.return_value = GET_PODS_RESPONSE_VIRT_API_POD
    check.kube_client.get_vms.return_value = GET_VMS_RESPONSE
    check.kube_client.get_vmis.return_value = GET_VMIS_RESPONSE["items"]

    dd_run_check(check)

    aggregator.assert_metric(
        "kubevirt_api.can_connect",
        value=1,
        tags=[
            "endpoint:https://10.244.0.38:443/healthz",
        ],
    )

    metrics_tags = [
        "endpoint:https://10.244.0.38:443/metrics",
        "kube_namespace:kubevirt",
        "kube_cluster_name:test-cluster",
        "pod_name:virt-api-7976d99767-cbj7g",
    ]

    aggregator.assert_metric("kubevirt_api.process.cpu_seconds.count", tags=metrics_tags)
    aggregator.assert_metric("kubevirt_api.process.max_fds", tags=metrics_tags)
    aggregator.assert_metric("kubevirt_api.process.open_fds", tags=metrics_tags)
    aggregator.assert_metric("kubevirt_api.process.resident_memory_bytes", tags=metrics_tags)
    aggregator.assert_metric("kubevirt_api.process.start_time_seconds", tags=metrics_tags)
    aggregator.assert_metric("kubevirt_api.process.virtual_memory_bytes", tags=metrics_tags)
    aggregator.assert_metric("kubevirt_api.process.virtual_memory_max_bytes", tags=metrics_tags)
    aggregator.assert_metric_has_tags("kubevirt_api.promhttp.metric_handler_requests_in_flight", tags=metrics_tags)
    aggregator.assert_metric_has_tags("kubevirt_api.promhttp.metric_handler_requests.count", tags=metrics_tags)
    aggregator.assert_metric_has_tags(
        "kubevirt_api.rest.client_rate_limiter_duration_seconds.bucket", tags=metrics_tags
    )
    aggregator.assert_metric_has_tags("kubevirt_api.rest.client_rate_limiter_duration_seconds.count", tags=metrics_tags)
    aggregator.assert_metric_has_tags("kubevirt_api.rest.client_rate_limiter_duration_seconds.sum", tags=metrics_tags)
    aggregator.assert_metric_has_tags("kubevirt_api.rest.client_request_latency_seconds.bucket", tags=metrics_tags)
    aggregator.assert_metric_has_tags("kubevirt_api.rest.client_request_latency_seconds.count", tags=metrics_tags)
    aggregator.assert_metric_has_tags("kubevirt_api.rest.client_request_latency_seconds.sum", tags=metrics_tags)
    aggregator.assert_metric_has_tags("kubevirt_api.rest.client_requests.count", tags=metrics_tags)

    # VM metrics
    vm_tags = [
        "vm_name:testvm",
        "vm_uid:4103f114-cf9d-47ad-9af0-be237ce7d4a1",
        "vm_size:small",
        "vm_domain:testvm",
        "kube_namespace:default",
    ]
    aggregator.assert_metric(
        "kubevirt_api.vm.count",
        value=1,
        tags=vm_tags,
    )

    # VMI metrics
    vmi_tags = [
        "kube_namespace:default",
        "vmi_domain:testvm",
        "vmi_name:testvm-2",
        "vmi_nodeName:dev-kubevirt-control-plane",
        "vmi_size:small",
        "vmi_uid:f1f3ae4b-f81f-406f-a574-f12e7e3ba4f2",
    ]
    aggregator.assert_metric(
        "kubevirt_api.vmi.count",
        value=1,
        tags=vmi_tags,
    )

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_emits_zero_can_connect_when_service_is_down(dd_run_check, aggregator, instance):
    check = KubevirtApiCheck("kubevirt_api", {}, [instance])
    check._setup = lambda: None
    check.kube_client = MagicMock()
    check.kube_client.get_pods.return_value = []
    check.kube_client.get_vms.return_value = []
    check.kube_client.get_vmis.return_value = []

    with pytest.raises(Exception):
        dd_run_check(check)
        aggregator.assert_metric(
            "kubevirt_api.can_connect",
            value=0,
            tags=[
                "endpoint:https://10.244.0.38:443/healthz",
            ],
        )


def test_emits_one_can_connect_when_service_is_up(dd_run_check, aggregator, instance, mocker):
    mocker.patch("requests.get", wraps=mock_http_responses)

    check = KubevirtApiCheck("kubevirt_api", {}, [instance])
    check._setup = lambda: None
    check.kube_client = MagicMock()
    check.kube_client.get_pods.return_value = GET_PODS_RESPONSE_VIRT_API_POD
    check.kube_client.get_vms.return_value = GET_VMS_RESPONSE
    check.kube_client.get_vmis.return_value = GET_VMIS_RESPONSE["items"]

    dd_run_check(check)
    aggregator.assert_metric(
        "kubevirt_api.can_connect",
        value=1,
        tags=[
            "endpoint:https://10.244.0.38:443/healthz",
        ],
    )
