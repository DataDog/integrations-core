# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.kubevirt_handler import KubeVirtHandlerCheck

from .conftest import mock_http_responses

base_tags = [
    "pod_name:virt-handler-some-id",
    "kube_namespace:kubevirt",
]


def test_check_collects_metrics(dd_run_check, aggregator, instance, mocker):
    mocker.patch("requests.get", wraps=mock_http_responses)
    check = KubeVirtHandlerCheck("kubevirt_handler", {}, [instance])
    dd_run_check(check)

    aggregator.assert_metric(
        "kubevirt_handler.can_connect",
        1,
        tags=["endpoint:https://127.0.0.1:8443/healthz", *base_tags],
    )

    metric_tags = [
        "kube_namespace:kubevirt",
        "pod_name:virt-handler-some-id",
    ]

    # aggregator.assert_metric_has_tags("kubevirt_handler.info", tags=metric_tags)  # gauge

    aggregator.assert_metric_has_tags(
        "kubevirt_handler.vmi.cpu_system_usage_seconds.count", tags=metric_tags
    )  # counter
    aggregator.assert_metric_has_tags("kubevirt_handler.vmi.cpu_usage_seconds.count", tags=metric_tags)  # counter
    aggregator.assert_metric_has_tags("kubevirt_handler.vmi.cpu_user_usage_seconds.count", tags=metric_tags)  # counter

    aggregator.assert_metric_has_tags("kubevirt_handler.vmi.memory_actual_balloon_bytes", tags=metric_tags)  # gauge
    aggregator.assert_metric_has_tags("kubevirt_handler.vmi.memory_available_bytes", tags=metric_tags)  # gauge
    aggregator.assert_metric_has_tags("kubevirt_handler.vmi.memory_domain_bytes", tags=metric_tags)  # gauge
    aggregator.assert_metric_has_tags("kubevirt_handler.vmi.memory_pgmajfault.count", tags=metric_tags)  # counter
    aggregator.assert_metric_has_tags("kubevirt_handler.vmi.memory_pgminfault.count", tags=metric_tags)  # counter
    aggregator.assert_metric_has_tags("kubevirt_handler.vmi.memory_resident_bytes", tags=metric_tags)  # gauge
    aggregator.assert_metric_has_tags("kubevirt_handler.vmi.memory_swap_in_traffic_bytes", tags=metric_tags)  # gauge
    aggregator.assert_metric_has_tags("kubevirt_handler.vmi.memory_swap_out_traffic_bytes", tags=metric_tags)  # gauge
    aggregator.assert_metric_has_tags("kubevirt_handler.vmi.memory_unused_bytes", tags=metric_tags)  # gauge
    aggregator.assert_metric_has_tags("kubevirt_handler.vmi.memory_usable_bytes", tags=metric_tags)  # gauge

    aggregator.assert_metric_has_tags("kubevirt_handler.vmi.network_receive_bytes.count", tags=metric_tags)  # counter
    aggregator.assert_metric_has_tags("kubevirt_handler.vmi.network_receive_errors.count", tags=metric_tags)  # counter
    aggregator.assert_metric_has_tags(
        "kubevirt_handler.vmi.network_receive_packets_dropped.count", tags=metric_tags
    )  # counter
    aggregator.assert_metric_has_tags("kubevirt_handler.vmi.network_receive_packets.count", tags=metric_tags)  # counter
    aggregator.assert_metric_has_tags("kubevirt_handler.vmi.network_transmit_bytes.count", tags=metric_tags)  # counter
    aggregator.assert_metric_has_tags("kubevirt_handler.vmi.network_transmit_errors.count", tags=metric_tags)  # counter
    aggregator.assert_metric_has_tags(
        "kubevirt_handler.vmi.network_transmit_packets_dropped.count", tags=metric_tags
    )  # counter
    aggregator.assert_metric_has_tags(
        "kubevirt_handler.vmi.network_transmit_packets.count", tags=metric_tags
    )  # counter

    aggregator.assert_metric_has_tags("kubevirt_handler.vmi.node_cpu_affinity", tags=metric_tags)  # gauge

    aggregator.assert_metric_has_tags("kubevirt_handler.vmi.storage_flush_requests.count", tags=metric_tags)  # counter
    aggregator.assert_metric_has_tags(
        "kubevirt_handler.vmi.storage_flush_times_seconds.count", tags=metric_tags
    )  # counter
    aggregator.assert_metric_has_tags("kubevirt_handler.vmi.storage_iops_read.count", tags=metric_tags)  # counter
    aggregator.assert_metric_has_tags("kubevirt_handler.vmi.storage_iops_write.count", tags=metric_tags)  # counter
    aggregator.assert_metric_has_tags(
        "kubevirt_handler.vmi.storage_read_times_seconds.count", tags=metric_tags
    )  # counter
    aggregator.assert_metric_has_tags(
        "kubevirt_handler.vmi.storage_read_traffic_bytes.count", tags=metric_tags
    )  # counter
    aggregator.assert_metric_has_tags(
        "kubevirt_handler.vmi.storage_write_times_seconds.count", tags=metric_tags
    )  # counter
    aggregator.assert_metric_has_tags(
        "kubevirt_handler.vmi.storage_write_traffic_bytes.count", tags=metric_tags
    )  # counter

    aggregator.assert_metric_has_tags("kubevirt_handler.vmi.vcpu_delay_seconds.count", tags=metric_tags)  # counter
    aggregator.assert_metric_has_tags("kubevirt_handler.vmi.vcpu_seconds.count", tags=metric_tags)  # counter
    aggregator.assert_metric_has_tags("kubevirt_handler.vmi.vcpu_wait_seconds.count", tags=metric_tags)  # counter

    aggregator.assert_metric_has_tags("kubevirt_handler.workqueue.adds.count", tags=metric_tags)  # counter
    aggregator.assert_metric_has_tags("kubevirt_handler.workqueue.depth", tags=metric_tags)  # gauge
    aggregator.assert_metric_has_tags(
        "kubevirt_handler.workqueue.longest_running_processor_seconds", tags=metric_tags
    )  # gauge
    aggregator.assert_metric_has_tags(
        "kubevirt_handler.workqueue.queue_duration_seconds.bucket", tags=metric_tags
    )  # histogram
    aggregator.assert_metric_has_tags(
        "kubevirt_handler.workqueue.queue_duration_seconds.sum", tags=metric_tags
    )  # histogram
    aggregator.assert_metric_has_tags(
        "kubevirt_handler.workqueue.queue_duration_seconds.count", tags=metric_tags
    )  # histogram
    aggregator.assert_metric_has_tags("kubevirt_handler.workqueue.retries.count", tags=metric_tags)  # counter
    aggregator.assert_metric_has_tags("kubevirt_handler.workqueue.unfinished_work_seconds", tags=metric_tags)  # gauge
    aggregator.assert_metric_has_tags(
        "kubevirt_handler.workqueue.work_duration_seconds.bucket", tags=metric_tags
    )  # histogram
    aggregator.assert_metric_has_tags(
        "kubevirt_handler.workqueue.work_duration_seconds.sum", tags=metric_tags
    )  # histogram
    aggregator.assert_metric_has_tags(
        "kubevirt_handler.workqueue.work_duration_seconds.count", tags=metric_tags
    )  # histogram

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_logs_warning_when_healthz_endpoint_is_missing(dd_run_check, aggregator, instance, mocker, caplog):
    mocker.patch("requests.get", wraps=mock_http_responses)
    del instance["kubevirt_handler_healthz_endpoint"]
    check = KubeVirtHandlerCheck("kubevirt_handler", {}, [instance])
    dd_run_check(check)
    assert (
        "Skipping health check. Please provide a `kubevirt_handler_healthz_endpoint` to ensure the health of the KubeVirt Handler."  # noqa: E501
        in caplog.text
        and "WARNING" in caplog.text
    )


def test_emits_can_connect_one_when_service_is_up(dd_run_check, aggregator, instance, mocker):
    mocker.patch("requests.get", wraps=mock_http_responses)
    check = KubeVirtHandlerCheck("kubevirt_handler", {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric(
        "kubevirt_handler.can_connect",
        1,
        tags=["endpoint:https://127.0.0.1:8443/healthz", *base_tags],
    )


def test_emits_can_connect_zero_when_service_is_down(dd_run_check, aggregator, instance):
    check = KubeVirtHandlerCheck("kubevirt_handler", {}, [instance])
    with pytest.raises(Exception):
        dd_run_check(check)

    aggregator.assert_metric(
        "kubevirt_handler.can_connect",
        0,
        tags=["endpoint:https://127.0.0.1:8443/healthz", *base_tags],
    )


def test_version_metadata(instance, dd_run_check, datadog_agent, aggregator, mocker):
    mocker.patch("requests.get", wraps=mock_http_responses)
    check = KubeVirtHandlerCheck("kubevirt_handler", {}, [instance])
    check.check_id = "test:123"
    dd_run_check(check)

    aggregator.assert_metric(
        "kubevirt_handler.can_connect",
        1,
        tags=["endpoint:https://127.0.0.1:8443/healthz", *base_tags],
    )

    version_metadata = {
        "version.scheme": "semver",
        "version.major": "1",
        "version.minor": "2",
        "version.patch": "2",
        "version.raw": "v1.2.2",
    }

    datadog_agent.assert_metadata("test:123", version_metadata)
