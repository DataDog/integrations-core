# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

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
        "fluxcd.process.resident_memory.bytes",
        "fluxcd.process.start_time.seconds",
        "fluxcd.process.virtual_memory.bytes",
        "fluxcd.process.virtual_memory.max.bytes",
        "fluxcd.workqueue.adds.count",
        "fluxcd.workqueue.depth",
        "fluxcd.workqueue.longest_running_processor.seconds",
        "fluxcd.workqueue.retries.count",
        "fluxcd.workqueue.unfinished_work.seconds",
    },
}


def test_mock_assert_metrics_v1(dd_run_check, aggregator, check, mock_metrics_v1):
    dd_run_check(check)
    for metric_name in EXPECTED_METRICS["v1"]:
        aggregator.assert_metric(metric_name)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_mock_assert_metrics_v2(dd_run_check, aggregator, check, mock_metrics_v2):
    dd_run_check(check)
    for metric_name in EXPECTED_METRICS["v2"]:
        aggregator.assert_metric(metric_name)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
