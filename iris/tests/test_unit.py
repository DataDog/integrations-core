# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from pathlib import Path
from typing import Callable

import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.base.types import InstanceType
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.iris import IrisCheck

FIXTURE_PATH = str(Path(__file__).parent / 'fixtures' / 'metrics.txt')


def test_check(
    dd_run_check: Callable[..., None],
    aggregator: AggregatorStub,
    instance: InstanceType,
    mock_http_response: Callable[..., None],
) -> None:
    mock_http_response(file_path=FIXTURE_PATH)
    check = IrisCheck('iris', {}, [instance])
    dd_run_check(check)
    dd_run_check(check)

    # The captured fixture was taken with a running interoperability production, so the
    # `iris_interop_*` block (51 series) is present alongside the base families: metadata.csv
    # describes exactly the union emitted by this single `api` catalog, so every metric it
    # declares must be observed and nothing observed may be undeclared.
    aggregator.assert_metrics_using_metadata(
        get_metadata_metrics(),
        check_submission_type=True,
        check_symmetric_inclusion=True,
    )

    aggregator.assert_service_check('iris.openmetrics.health', ServiceCheck.OK)


def test_interop_host_label_renamed(
    dd_run_check: Callable[..., None],
    aggregator: AggregatorStub,
    instance: InstanceType,
    mock_http_response: Callable[..., None],
) -> None:
    """
    `host` collides with the reserved Datadog infra-hostname tag key, so the check renames it
    to `interop_host` on every interoperability family that carries it. The value must still be
    surfaced as a tag, just under the collision-safe key.
    """
    mock_http_response(file_path=FIXTURE_PATH)
    check = IrisCheck('iris', {}, [instance])
    dd_run_check(check)
    dd_run_check(check)

    interop_host_metrics = (
        'iris.interop.hosts',
        'iris.interop.last_activity',
        'iris.interop.messages.count',
        'iris.interop.messages.errored',
        'iris.interop.messages.per_sec.count',
    )
    for metric_name in interop_host_metrics:
        aggregator.assert_metric_has_tag_prefix(metric_name, 'interop_host:')
        for metric in aggregator.metrics(metric_name):
            assert not any(tag.startswith('host:') for tag in metric.tags), (
                f"{metric_name} must not carry a raw 'host:' tag sourced from the exposition"
            )


def test_system_info_version_label_renamed(
    dd_run_check: Callable[..., None],
    aggregator: AggregatorStub,
    instance: InstanceType,
    mock_http_response: Callable[..., None],
) -> None:
    """
    `version` collides with Datadog's reserved software-version tracking facet, so the check
    renames it to `iris_version` on `iris_system_info`. The IRIS product version value must
    still be present as a tag, just under the collision-safe key.
    """
    mock_http_response(file_path=FIXTURE_PATH)
    check = IrisCheck('iris', {}, [instance])
    dd_run_check(check)
    dd_run_check(check)

    aggregator.assert_metric_has_tag('iris.system.info', 'iris_version:2026.1')
    for metric in aggregator.metrics('iris.system.info'):
        assert not any(tag.startswith('version:') for tag in metric.tags), (
            "iris.system.info must not carry a raw 'version:' tag sourced from the exposition"
        )
        # Other descriptor labels on this info metric pass through unrenamed.
        assert any(tag.startswith('product:') for tag in metric.tags)
        assert any(tag.startswith('platform:') for tag in metric.tags)
        assert any(tag.startswith('build_number:') for tag in metric.tags)
        assert any(tag.startswith('build_date:') for tag in metric.tags)


def test_id_label_passthrough(
    dd_run_check: Callable[..., None],
    aggregator: AggregatorStub,
    instance: InstanceType,
    mock_http_response: Callable[..., None],
) -> None:
    """
    Unlike `host`/`version`, the generic `id` label is deliberately left unrenamed across every
    family that carries it, since it means different things per family and a global rename
    would not add real disambiguation.
    """
    mock_http_response(file_path=FIXTURE_PATH)
    check = IrisCheck('iris', {}, [instance])
    dd_run_check(check)
    dd_run_check(check)

    aggregator.assert_metric_has_tag('iris.cpu.pct', 'id:AUXWD')
    aggregator.assert_metric_has_tag('iris.cpu.pct', 'id:CSPSRV')


@pytest.mark.parametrize(
    'metric_name, tag',
    [
        ('iris.process', 'namespace:USER'),
        ('iris.process', 'jobtype:2'),
        ('iris.process', 'routine:Ens.Queue.1'),
        ('iris.process', 'state:EVTW'),
        ('iris.db.size_mb', 'dir:/usr/irissys/mgr/user/'),
        ('iris.interop.hosts', 'production:Demo.MonitorProduction'),
        ('iris.interop.hosts', 'status:OK'),
    ],
)
def test_other_labels_passthrough(
    dd_run_check: Callable[..., None],
    aggregator: AggregatorStub,
    instance: InstanceType,
    mock_http_response: Callable[..., None],
    metric_name: str,
    tag: str,
) -> None:
    """
    All other labels (`dir`, `namespace`, `jobtype`, `routine`, `state`, and, on interop
    metrics, `production`/`status`) pass through verbatim, unlike `host`/`version`.
    """
    mock_http_response(file_path=FIXTURE_PATH)
    check = IrisCheck('iris', {}, [instance])
    dd_run_check(check)
    dd_run_check(check)

    aggregator.assert_metric_has_tag(metric_name, tag)


def test_health_service_check_critical_then_ok(
    dd_run_check: Callable[..., None],
    aggregator: AggregatorStub,
    instance: InstanceType,
    mock_http_response: Callable[..., None],
) -> None:
    """
    `enable_health_service_check` is left at the framework default, so a connection/parse
    failure must report CRITICAL and a subsequent successful scrape must return it to OK.
    """
    mock_http_response(status_code=500)
    check = IrisCheck('iris', {}, [instance])
    with pytest.raises(Exception):
        dd_run_check(check)

    aggregator.assert_service_check('iris.openmetrics.health', ServiceCheck.CRITICAL)

    aggregator.reset()
    mock_http_response(file_path=FIXTURE_PATH)
    dd_run_check(check)

    aggregator.assert_service_check('iris.openmetrics.health', ServiceCheck.OK)
