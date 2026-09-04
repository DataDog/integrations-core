# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from collections.abc import Callable

import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.base.types import InstanceType
from datadog_checks.intersystems_iris import IrisCheck

from .common import FIXTURE_PATH, assert_healthy_scrape

pytestmark = pytest.mark.unit

# The fixture was captured from a busy ECP data server with a live client attached and a
# running interoperability production, so the always-on `iris_interop_*` interface family, the
# per-connection `iris_ecps_*` family and the work queue family are all present alongside the
# base families.
FIXTURE_EMITTED_PREFIXES = ('intersystems_iris.ecps.', 'intersystems_iris.wqm.')


def test_check(scraped_aggregator: AggregatorStub) -> None:
    assert_healthy_scrape(scraped_aggregator, FIXTURE_EMITTED_PREFIXES)


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
        'intersystems_iris.interop.messages.per_sec',
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
        ('intersystems_iris.cpu.pct', 'id:AUXWD'),
        ('intersystems_iris.cpu.pct', 'id:CSPSRV'),
    ],
)
def test_other_labels_passthrough(scraped_aggregator: AggregatorStub, metric_name: str, tag: str) -> None:
    """
    All other labels (`dir`, `namespace`, `jobtype`, `routine`, `state`, the ECP data-server
    connection `id`, the per-process `id`, and, on interop metrics, `production`/`status`) pass
    through verbatim, unlike `host`/`version`. `id` in particular is deliberately left unrenamed
    even though it means something different per family, since a global rename would not add real
    disambiguation.
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
    # `dd_run_check` re-raises the check's failure as a bare `Exception` carrying the formatted
    # traceback, so the concrete `requests.HTTPError` never reaches us -- match on the message to
    # confirm the scrape really is what failed, rather than accepting any error at all.
    with pytest.raises(Exception, match='500 Server Error'):
        dd_run_check(check)

    aggregator.assert_service_check('intersystems_iris.openmetrics.health', ServiceCheck.CRITICAL)

    aggregator.reset()
    mock_http_response(file_path=FIXTURE_PATH)
    dd_run_check(check)

    aggregator.assert_service_check('intersystems_iris.openmetrics.health', ServiceCheck.OK)
