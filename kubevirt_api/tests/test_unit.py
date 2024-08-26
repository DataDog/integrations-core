# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from copy import deepcopy
from unittest.mock import MagicMock

import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.kubevirt_api import KubeVirtApiCheck

from .conftest import mock_http_responses
from .constants import BAD_METRICS_HOSTNAME_INSTANCE, HEALTHZ_TAGS
from .mock_response import GET_VMIS_RESPONSE, GET_VMS_RESPONSE

pytestmark = [pytest.mark.unit]


def test_check_collects_all_metrics(dd_run_check, aggregator, instance, mocker):
    mocker.patch("requests.get", wraps=mock_http_responses)

    check = KubeVirtApiCheck("kubevirt_api", {}, [instance])

    check._setup_kube_client = lambda: None
    check.kube_client = MagicMock()
    check.kube_client.get_vms.return_value = GET_VMS_RESPONSE["items"]
    check.kube_client.get_vmis.return_value = GET_VMIS_RESPONSE["items"]

    dd_run_check(check)

    aggregator.assert_metric(
        "kubevirt_api.can_connect",
        value=1,
        tags=HEALTHZ_TAGS,
    )

    metrics_tags = [
        "endpoint:https://10.244.0.38:443/metrics",
        "kube_namespace:kubevirt",
        "pod_name:virt-api-98cf864cc-zkgcd",
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
        "kube_namespace:default",
        "vm_name:testvm",
        "vm_uid:46bc4e2b-d287-4408-8393-c7accdd73291",
        "vm_size:small",
        "vm_domain:testvm",
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
        "vmi_phase:Running",
    ]
    aggregator.assert_metric(
        "kubevirt_api.vmi.count",
        value=1,
        tags=vmi_tags,
    )

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_check_sends_zero_count_for_vms(dd_run_check, aggregator, instance, mocker):
    mocker.patch("requests.get", wraps=mock_http_responses)

    check = KubeVirtApiCheck("kubevirt_api", {}, [instance])

    check._setup_kube_client = lambda: None
    check.kube_client = MagicMock()
    check.kube_client.get_vms.return_value = []
    check.kube_client.get_vmis.return_value = []

    dd_run_check(check)

    aggregator.assert_metric(
        "kubevirt_api.can_connect",
        value=1,
        tags=HEALTHZ_TAGS,
    )

    aggregator.assert_metric("kubevirt_api.vm.count", value=0)


def test_check_sends_zero_count_for_vmis(dd_run_check, aggregator, instance, mocker):
    mocker.patch("requests.get", wraps=mock_http_responses)

    check = KubeVirtApiCheck("kubevirt_api", {}, [instance])

    check._setup_kube_client = lambda: None
    check.kube_client = MagicMock()
    check.kube_client.get_vms.return_value = []
    check.kube_client.get_vmis.return_value = []

    dd_run_check(check)

    aggregator.assert_metric(
        "kubevirt_api.can_connect",
        value=1,
        tags=HEALTHZ_TAGS,
    )

    aggregator.assert_metric("kubevirt_api.vmi.count", value=0)


def test_emits_zero_can_connect_when_service_is_down(dd_run_check, aggregator, instance):
    check = KubeVirtApiCheck("kubevirt_api", {}, [instance])
    check._setup_kube_client = lambda: None
    check.kube_client = MagicMock()
    check.kube_client.get_vms.return_value = []
    check.kube_client.get_vmis.return_value = []

    with pytest.raises(Exception):
        dd_run_check(check)

    aggregator.assert_metric(
        "kubevirt_api.can_connect",
        value=0,
        tags=HEALTHZ_TAGS,
    )


def test_emits_one_can_connect_when_service_is_up(dd_run_check, aggregator, instance, mocker):
    mocker.patch("requests.get", wraps=mock_http_responses)

    check = KubeVirtApiCheck("kubevirt_api", {}, [instance])
    check._setup_kube_client = lambda: None
    check.kube_client = MagicMock()
    check.kube_client.get_vms.return_value = GET_VMS_RESPONSE["items"]
    check.kube_client.get_vmis.return_value = GET_VMIS_RESPONSE["items"]

    dd_run_check(check)
    aggregator.assert_metric(
        "kubevirt_api.can_connect",
        value=1,
        tags=HEALTHZ_TAGS,
    )


def test_raise_exception_when_metrics_endpoint_is_bad(dd_run_check, aggregator, instance, mocker):
    mocker.patch("requests.get", wraps=mock_http_responses)

    check = KubeVirtApiCheck("kubevirt_api", {}, [BAD_METRICS_HOSTNAME_INSTANCE])
    check._setup_kube_client = lambda: None
    check.kube_client = MagicMock()
    check.kube_client.get_vms.return_value = GET_VMS_RESPONSE["items"]
    check.kube_client.get_vmis.return_value = GET_VMIS_RESPONSE["items"]

    with pytest.raises(Exception):
        dd_run_check(check)

    aggregator.assert_metric(
        "kubevirt_api.can_connect",
        value=1,
        tags=HEALTHZ_TAGS,
    )


def test_raise_exception_cannot_connect_to_kubernetes_api(dd_run_check, aggregator, instance, mocker, caplog):
    mocker.patch("requests.get", wraps=mock_http_responses)

    check = KubeVirtApiCheck("kubevirt_api", {}, [instance])
    with pytest.raises(
        Exception,
    ):
        dd_run_check(check)

    assert "Cannot connect to Kubernetes API:" in caplog.text


def test_log_warning_healthz_endpoint_not_provided(dd_run_check, aggregator, instance, mocker, caplog):
    mocker.patch("requests.get", wraps=mock_http_responses)

    new_instance = deepcopy(instance)
    new_instance.pop("kubevirt_api_healthz_endpoint")

    check = KubeVirtApiCheck("kubevirt_api", {}, [new_instance])

    check._setup_kube_client = lambda: None
    check.kube_client = MagicMock()
    check.kube_client.get_vms.return_value = GET_VMS_RESPONSE["items"]
    check.kube_client.get_vmis.return_value = GET_VMIS_RESPONSE["items"]

    dd_run_check(check)

    assert (
        "Skipping health check. Please provide a `kubevirt_api_healthz_endpoint` to ensure the health of the KubeVirt API."  # noqa: E501
        in caplog.text
    )
