import pytest

from datadog_checks.dev.utils import get_metadata_metrics

EXPECTED_METRICS = {
    "fluxcd.gotk.reconcile.condition",
    "fluxcd.gotk.suspend.status",
    "fluxcd.gotk.reconcile.duration.seconds.count",
    "fluxcd.gotk.reconcile.duration.seconds.sum",
    "fluxcd.gotk.reconcile.duration.seconds.bucket",
    "fluxcd.controller.runtime.active.workers",
    "fluxcd.controller.runtime.reconcile.count",
    "fluxcd.controller.runtime.reconcile.time.seconds.count",
    "fluxcd.controller.runtime.reconcile.time.seconds.sum",
    "fluxcd.controller.runtime.reconcile.time.seconds.bucket",
    "fluxcd.controller.runtime.max.concurrent.reconciles",
    "fluxcd.controller.runtime.reconcile.errors.count",
}


@pytest.mark.unit
def test_mock_assert_metrics(dd_run_check, aggregator, check, mock_metrics):
    dd_run_check(check)
    for metric_name in EXPECTED_METRICS:
        aggregator.assert_metric(metric_name)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
