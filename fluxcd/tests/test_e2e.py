# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.dev.utils import get_metadata_metrics

from .common import EXPECTED_METRICS


def test_source_controller_metrics(dd_agent_check):
    """
    This only tests version 2 of flux.

    Version 1 is in maintenance mode, all our users are on version 2.
    """
    aggregator = dd_agent_check()
    ignore = {
        'fluxcd.controller.runtime.reconcile.count',
        'fluxcd.controller.runtime.reconcile.errors.count',
        'fluxcd.controller.runtime.reconcile.time.seconds.bucket',
        'fluxcd.controller.runtime.reconcile.time.seconds.count',
        'fluxcd.controller.runtime.reconcile.time.seconds.sum',
        'fluxcd.gotk.reconcile.condition',
        'fluxcd.gotk.reconcile.duration.seconds.bucket',
        'fluxcd.gotk.reconcile.duration.seconds.count',
        'fluxcd.gotk.reconcile.duration.seconds.sum',
        'fluxcd.gotk.suspend.status',
        'fluxcd.process.cpu_seconds.count',
        'fluxcd.workqueue.adds.count',
        'fluxcd.workqueue.retries.count',
    }
    for metric_name in set(EXPECTED_METRICS['v2']) - ignore:
        aggregator.assert_metric(metric_name)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
