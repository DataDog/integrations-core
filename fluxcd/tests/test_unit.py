# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.utils import get_metadata_metrics

EXPECTED_METRICS = {
    "v1": {
        "fluxcd.controller.runtime.active.workers",
        "fluxcd.controller.runtime.max.concurrent.reconciles",
        "fluxcd.controller.runtime.reconcile.count",
        "fluxcd.controller.runtime.reconcile.errors.count",
        "fluxcd.controller.runtime.reconcile.time.seconds.bucket",
        "fluxcd.controller.runtime.reconcile.time.seconds.count",
        "fluxcd.controller.runtime.reconcile.time.seconds.sum",
        "fluxcd.gotk.reconcile.condition",
        "fluxcd.gotk.reconcile.duration.seconds.bucket",
        "fluxcd.gotk.reconcile.duration.seconds.count",
        "fluxcd.gotk.reconcile.duration.seconds.sum",
        "fluxcd.gotk.suspend.status",
    },
    "v2": {
        "fluxcd.controller.runtime.active.workers",
        "fluxcd.controller.runtime.max.concurrent.reconciles",
        "fluxcd.controller.runtime.reconcile.count",
        "fluxcd.controller.runtime.reconcile.errors.count",
        "fluxcd.controller.runtime.reconcile.time.seconds.bucket",
        "fluxcd.controller.runtime.reconcile.time.seconds.count",
        "fluxcd.controller.runtime.reconcile.time.seconds.sum",
        "fluxcd.gotk.reconcile.condition",
        "fluxcd.gotk.reconcile.duration.seconds.bucket",
        "fluxcd.gotk.reconcile.duration.seconds.count",
        "fluxcd.gotk.reconcile.duration.seconds.sum",
        "fluxcd.gotk.suspend.status",
        "fluxcd.leader_election_master_status",
        "fluxcd.process.cpu_seconds.count",
        "fluxcd.process.max_fds",
        "fluxcd.process.open_fds",
        "fluxcd.process.resident_memory",
        "fluxcd.process.start_time",
        "fluxcd.process.virtual_memory",
        "fluxcd.process.virtual_memory.max",
        "fluxcd.workqueue.adds.count",
        "fluxcd.workqueue.depth",
        "fluxcd.workqueue.longest_running_processor",
        "fluxcd.workqueue.retries.count",
        "fluxcd.workqueue.unfinished_work",
    },
}


@pytest.mark.parametrize("fluxcd_version", ["v1", "v2"])
def test_assert_metrics(dd_run_check, aggregator, check, request, fluxcd_version):
    _mock_response = request.getfixturevalue(f"mock_metrics_{fluxcd_version}")
    dd_run_check(check)
    for metric_name in EXPECTED_METRICS[fluxcd_version]:
        aggregator.assert_metric(metric_name)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
