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
from datadog_checks.intersystems_iris import IrisCheck

from .common import unconditional_metadata_metrics

FIXTURE_PATH = str(Path(__file__).parent / 'fixtures' / 'metrics.txt')

# The fixture was captured with a running interoperability production and from an ECP data
# server with a live client attached, so the always-on `iris_interop_*` interface family and the
# per-connection `iris_ecps_*` family are both present alongside the base families.
FIXTURE_TOPOLOGY_PREFIXES = ('intersystems_iris.ecps.',)


def test_check(scraped_aggregator: AggregatorStub) -> None:
    # Nothing may be submitted that metadata.csv does not declare, and the declared types must
    # match what the check submits.
    scraped_aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)

    # Conversely, every metric the catalog declares for this exposition must have been
    # collected -- this is what catches a metadata.csv entry with no emitter behind it. The
    # families the fixture cannot cover are documented in `common.py`.
    scraped_aggregator.assert_metrics_using_metadata(
        unconditional_metadata_metrics(get_metadata_metrics(), FIXTURE_TOPOLOGY_PREFIXES),
        check_submission_type=True,
        check_symmetric_inclusion=True,
    )

    scraped_aggregator.assert_service_check('intersystems_iris.openmetrics.health', ServiceCheck.OK)


def test_interop_host_label_renamed(scraped_aggregator: AggregatorStub) -> None:
    """
    `host` collides with the reserved Datadog infra-hostname tag key, so the check renames it
    to `interop_host` on every interoperability family that carries it. The value must still be
    surfaced as a tag, just under the collision-safe key.
    """
    interop_host_metrics = (
        'intersystems_iris.interop.hosts',
        'intersystems_iris.interop.last_activity',
        'intersystems_iris.interop.messages.count',
        'intersystems_iris.interop.messages.errored',
        'intersystems_iris.interop.messages.per_sec.count',
    )
    for metric_name in interop_host_metrics:
        scraped_aggregator.assert_metric_has_tag_prefix(metric_name, 'interop_host:')
        for metric in scraped_aggregator.metrics(metric_name):
            assert not any(tag.startswith('host:') for tag in metric.tags), (
                f"{metric_name} must not carry a raw 'host:' tag sourced from the exposition"
            )


def test_system_info_version_label_renamed(scraped_aggregator: AggregatorStub) -> None:
    """
    `version` collides with Datadog's reserved software-version tracking facet, so the check
    renames it to `iris_version` on `iris_system_info`. The IRIS product version value must
    still be present as a tag, just under the collision-safe key.
    """
    scraped_aggregator.assert_metric_has_tag('intersystems_iris.system.info', 'iris_version:2026.1')
    for metric in scraped_aggregator.metrics('intersystems_iris.system.info'):
        assert not any(tag.startswith('version:') for tag in metric.tags), (
            "intersystems_iris.system.info must not carry a raw 'version:' tag sourced from the exposition"
        )
        # Other descriptor labels on this info metric pass through unrenamed.
        assert any(tag.startswith('product:') for tag in metric.tags)
        assert any(tag.startswith('platform:') for tag in metric.tags)
        assert any(tag.startswith('build_number:') for tag in metric.tags)
        assert any(tag.startswith('build_date:') for tag in metric.tags)


def test_id_label_passthrough(scraped_aggregator: AggregatorStub) -> None:
    """
    Unlike `host`/`version`, the generic `id` label is deliberately left unrenamed across every
    family that carries it, since it means different things per family and a global rename
    would not add real disambiguation.
    """
    scraped_aggregator.assert_metric_has_tag('intersystems_iris.cpu.pct', 'id:AUXWD')
    scraped_aggregator.assert_metric_has_tag('intersystems_iris.cpu.pct', 'id:CSPSRV')


@pytest.mark.parametrize(
    'metric_name, tag',
    [
        ('intersystems_iris.process', 'namespace:USER'),
        ('intersystems_iris.process', 'jobtype:2'),
        ('intersystems_iris.process', 'routine:Ens.Queue.1'),
        ('intersystems_iris.process', 'state:EVTW'),
        ('intersystems_iris.db.size_mb', 'dir:/usr/irissys/mgr/user/'),
        ('intersystems_iris.interop.hosts', 'production:Demo.MonitorProduction'),
        ('intersystems_iris.interop.hosts', 'status:OK'),
        ('intersystems_iris.ecps.glo_ref.count', 'id:IRISAPP:IRIS-APP-01:IRIS'),
    ],
)
def test_other_labels_passthrough(scraped_aggregator: AggregatorStub, metric_name: str, tag: str) -> None:
    """
    All other labels (`dir`, `namespace`, `jobtype`, `routine`, `state`, the ECP data-server
    connection `id`, and, on interop metrics, `production`/`status`) pass through verbatim,
    unlike `host`/`version`.
    """
    scraped_aggregator.assert_metric_has_tag(metric_name, tag)


def test_instance_rename_labels_merge_with_defaults(instance: InstanceType) -> None:
    """
    An instance-level `rename_labels` must merge into, rather than replace, the
    collision-avoiding defaults -- otherwise renaming any one label would resurrect the
    reserved `host`/`version` tag keys.
    """
    config = {**instance, 'rename_labels': {'namespace': 'iris_namespace', 'host': 'iris_host'}}
    check = IrisCheck('intersystems_iris', {}, [config])

    assert check.get_config_with_defaults(config)['rename_labels'] == {
        # Overridden by the instance...
        'host': 'iris_host',
        # ...while the default the instance did not mention survives.
        'version': 'iris_version',
        'namespace': 'iris_namespace',
    }


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
    check = IrisCheck('intersystems_iris', {}, [instance])
    with pytest.raises(Exception):
        dd_run_check(check)

    aggregator.assert_service_check('intersystems_iris.openmetrics.health', ServiceCheck.CRITICAL)

    aggregator.reset()
    mock_http_response(file_path=FIXTURE_PATH)
    dd_run_check(check)

    aggregator.assert_service_check('intersystems_iris.openmetrics.health', ServiceCheck.OK)
