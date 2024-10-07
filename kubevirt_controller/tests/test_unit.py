# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.kubevirt_controller import KubeVirtControllerCheck

from .conftest import mock_http_responses

base_tags = [
    "pod_name:virt-controller-some-id",
    "kube_namespace:kubevirt",
]


def test_emits_can_connect_one_when_service_is_up(dd_run_check, aggregator, instance, mocker):
    mocker.patch("requests.get", wraps=mock_http_responses)
    check = KubeVirtControllerCheck("kubevirt_controller", {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric(
        "kubevirt_controller.can_connect",
        value=1,
        tags=["endpoint:https://10.244.0.38:443/healthz", *base_tags],
    )


def test_emits_can_connect_zero_when_service_is_down(dd_run_check, aggregator, instance):
    check = KubeVirtControllerCheck("kubevirt_controller", {}, [instance])
    with pytest.raises(Exception):
        dd_run_check(check)
    aggregator.assert_metric(
        "kubevirt_controller.can_connect", value=0, tags=["endpoint:https://10.244.0.38:443/healthz", *base_tags]
    )


def test_check_collects_all_metrics(dd_run_check, aggregator, instance, mocker):
    mocker.patch("requests.get", wraps=mock_http_responses)

    check = KubeVirtControllerCheck("kubevirt_controller", {}, [instance])

    dd_run_check(check)

    aggregator.assert_metric(
        "kubevirt_controller.can_connect",
        value=1,
        tags=["endpoint:https://10.244.0.38:443/healthz", *base_tags],
    )

    aggregator.assert_metric_has_tags("kubevirt_controller.virt_controller.leading_status", tags=base_tags)
    aggregator.assert_metric_has_tags("kubevirt_controller.virt_controller.ready_status", tags=base_tags)
    aggregator.assert_metric_has_tags(
        "kubevirt_controller.vm.error_status_last_transition_timestamp_seconds.count", tags=base_tags
    )
    aggregator.assert_metric_has_tags(
        "kubevirt_controller.vm.migrating_status_last_transition_timestamp_seconds.count", tags=base_tags
    )
    aggregator.assert_metric_has_tags(
        "kubevirt_controller.vm.non_running_status_last_transition_timestamp_seconds.count", tags=base_tags
    )
    aggregator.assert_metric_has_tags(
        "kubevirt_controller.vm.running_status_last_transition_timestamp_seconds.count", tags=base_tags
    )
    aggregator.assert_metric_has_tags(
        "kubevirt_controller.vm.starting_status_last_transition_timestamp_seconds.count", tags=base_tags
    )
    aggregator.assert_metric_has_tags("kubevirt_controller.vmi.migrations_in_pending_phase", tags=base_tags)
    aggregator.assert_metric_has_tags("kubevirt_controller.vmi.migrations_in_running_phase", tags=base_tags)
    aggregator.assert_metric_has_tags("kubevirt_controller.vmi.migrations_in_scheduling_phase", tags=base_tags)
    aggregator.assert_metric_has_tags("kubevirt_controller.vmi.non_evictable", tags=base_tags)
    aggregator.assert_metric_has_tags("kubevirt_controller.vmi.number_of_outdated", tags=base_tags)
    aggregator.assert_metric_has_tags("kubevirt_controller.vmi.phase_count", tags=base_tags)
    aggregator.assert_metric_has_tags(
        "kubevirt_controller.vmi.phase_transition_time_from_creation_seconds.sum", tags=base_tags
    )
    aggregator.assert_metric_has_tags(
        "kubevirt_controller.vmi.phase_transition_time_from_creation_seconds.bucket", tags=base_tags
    )
    aggregator.assert_metric_has_tags(
        "kubevirt_controller.vmi.phase_transition_time_from_creation_seconds.count", tags=base_tags
    )
    aggregator.assert_metric_has_tags(
        "kubevirt_controller.vmi.phase_transition_time_from_deletion_seconds.sum", tags=base_tags
    )
    aggregator.assert_metric_has_tags(
        "kubevirt_controller.vmi.phase_transition_time_from_deletion_seconds.bucket", tags=base_tags
    )
    aggregator.assert_metric_has_tags(
        "kubevirt_controller.vmi.phase_transition_time_from_deletion_seconds.count", tags=base_tags
    )
    aggregator.assert_metric_has_tags("kubevirt_controller.vmi.phase_transition_time_seconds.sum", tags=base_tags)
    aggregator.assert_metric_has_tags("kubevirt_controller.vmi.phase_transition_time_seconds.bucket", tags=base_tags)
    aggregator.assert_metric_has_tags("kubevirt_controller.vmi.phase_transition_time_seconds.count", tags=base_tags)
    aggregator.assert_metric_has_tags("kubevirt_controller.workqueue.adds.count", tags=base_tags)
    aggregator.assert_metric_has_tags("kubevirt_controller.workqueue.depth", tags=base_tags)
    aggregator.assert_metric_has_tags("kubevirt_controller.workqueue.longest_running_processor_seconds", tags=base_tags)
    aggregator.assert_metric_has_tags("kubevirt_controller.workqueue.queue_duration_seconds.sum", tags=base_tags)
    aggregator.assert_metric_has_tags("kubevirt_controller.workqueue.queue_duration_seconds.bucket", tags=base_tags)
    aggregator.assert_metric_has_tags("kubevirt_controller.workqueue.queue_duration_seconds.count", tags=base_tags)
    aggregator.assert_metric_has_tags("kubevirt_controller.workqueue.retries.count", tags=base_tags)
    aggregator.assert_metric_has_tags("kubevirt_controller.workqueue.unfinished_work_seconds", tags=base_tags)
    aggregator.assert_metric_has_tags("kubevirt_controller.workqueue.work_duration_seconds.sum", tags=base_tags)
    aggregator.assert_metric_has_tags("kubevirt_controller.workqueue.work_duration_seconds.bucket", tags=base_tags)
    aggregator.assert_metric_has_tags("kubevirt_controller.workqueue.work_duration_seconds.count", tags=base_tags)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
