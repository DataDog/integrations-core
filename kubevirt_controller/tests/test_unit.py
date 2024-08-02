# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.kubevirt_controller import KubevirtControllerCheck

from .conftest import mock_http_responses


def test_emits_can_connect_one_when_service_is_up(dd_run_check, aggregator, instance, mocker):
    mocker.patch("requests.get", wraps=mock_http_responses)
    check = KubevirtControllerCheck("kubevirt_controller", {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric(
        "kubevirt_controller.can_connect",
        value=1,
        tags=[
            "endpoint:https://10.244.0.38:443/healthz",
        ],
    )


def test_emits_can_connect_zero_when_service_is_down(dd_run_check, aggregator, instance):
    check = KubevirtControllerCheck("kubevirt_controller", {}, [instance])
    with pytest.raises(Exception):
        dd_run_check(check)
    aggregator.assert_metric(
        "kubevirt_controller.can_connect", value=0, tags=["endpoint:https://10.244.0.38:443/healthz"]
    )


def test_check_collects_all_metrics(dd_run_check, aggregator, instance, mocker):
    mocker.patch("requests.get", wraps=mock_http_responses)

    check = KubevirtControllerCheck("kubevirt_controller", {}, [instance])

    dd_run_check(check)

    aggregator.assert_metric(
        "kubevirt_controller.can_connect",
        value=1,
        tags=[
            "endpoint:https://10.244.0.38:443/healthz",
        ],
    )

    aggregator.assert_metric("kubevirt_controller.virt_controller.leading_status")
    aggregator.assert_metric("kubevirt_controller.virt_controller.ready_status")
    aggregator.assert_metric("kubevirt_controller.vm.error_status_last_transition_timestamp_seconds.count")
    aggregator.assert_metric("kubevirt_controller.vm.migrating_status_last_transition_timestamp_seconds.count")
    aggregator.assert_metric("kubevirt_controller.vm.non_running_status_last_transition_timestamp_seconds.count")
    aggregator.assert_metric("kubevirt_controller.vm.running_status_last_transition_timestamp_seconds.count")
    aggregator.assert_metric("kubevirt_controller.vm.starting_status_last_transition_timestamp_seconds.count")
    aggregator.assert_metric("kubevirt_controller.vmi.migrations_in_pending_phase")
    aggregator.assert_metric("kubevirt_controller.vmi.migrations_in_running_phase")
    aggregator.assert_metric("kubevirt_controller.vmi.migrations_in_scheduling_phase")
    aggregator.assert_metric("kubevirt_controller.vmi.non_evictable")
    aggregator.assert_metric("kubevirt_controller.vmi.number_of_outdated")
    aggregator.assert_metric("kubevirt_controller.vmi.phase_count")
    aggregator.assert_metric("kubevirt_controller.vmi.phase_transition_time_from_creation_seconds.sum")
    aggregator.assert_metric("kubevirt_controller.vmi.phase_transition_time_from_creation_seconds.bucket")
    aggregator.assert_metric("kubevirt_controller.vmi.phase_transition_time_from_creation_seconds.count")
    aggregator.assert_metric("kubevirt_controller.vmi.phase_transition_time_from_deletion_seconds.sum")
    aggregator.assert_metric("kubevirt_controller.vmi.phase_transition_time_from_deletion_seconds.bucket")
    aggregator.assert_metric("kubevirt_controller.vmi.phase_transition_time_from_deletion_seconds.count")
    aggregator.assert_metric("kubevirt_controller.vmi.phase_transition_time_seconds.sum")
    aggregator.assert_metric("kubevirt_controller.vmi.phase_transition_time_seconds.bucket")
    aggregator.assert_metric("kubevirt_controller.vmi.phase_transition_time_seconds.count")
    aggregator.assert_metric("kubevirt_controller.workqueue.adds.count")
    aggregator.assert_metric("kubevirt_controller.workqueue.depth")
    aggregator.assert_metric("kubevirt_controller.workqueue.longest_running_processor_seconds")
    aggregator.assert_metric("kubevirt_controller.workqueue.queue_duration_seconds.sum")
    aggregator.assert_metric("kubevirt_controller.workqueue.queue_duration_seconds.bucket")
    aggregator.assert_metric("kubevirt_controller.workqueue.queue_duration_seconds.count")
    aggregator.assert_metric("kubevirt_controller.workqueue.retries.count")
    aggregator.assert_metric("kubevirt_controller.workqueue.unfinished_work_seconds")
    aggregator.assert_metric("kubevirt_controller.workqueue.work_duration_seconds.sum")
    aggregator.assert_metric("kubevirt_controller.workqueue.work_duration_seconds.bucket")
    aggregator.assert_metric("kubevirt_controller.workqueue.work_duration_seconds.count")

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
