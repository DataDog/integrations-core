# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest
from clickhouse_driver.errors import Error, NetworkError

from datadog_checks.clickhouse import ClickhouseCheck
from datadog_checks.dev.utils import get_metadata_metrics

from .common import CLICKHOUSE_VERSION
from .metrics import OPTIONAL_METRICS, get_metrics

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]


def test_check(aggregator, instance, dd_run_check):
    check = ClickhouseCheck('clickhouse', {}, [instance])
    dd_run_check(check)
    server_tag = 'server:{}'.format(instance['server'])
    port_tag = 'port:{}'.format(instance['port'])
    metrics = get_metrics(CLICKHOUSE_VERSION)

    for metric in metrics:
        aggregator.assert_metric_has_tag(metric, port_tag, at_least=1)
        aggregator.assert_metric_has_tag(metric, server_tag, at_least=1)
        aggregator.assert_metric_has_tag(metric, 'db:default', at_least=1)
        aggregator.assert_metric_has_tag(metric, 'foo:bar', at_least=1)

    aggregator.assert_metric(
        'clickhouse.dictionary.item.current',
        tags=[server_tag, port_tag, 'db:default', 'foo:bar', 'dictionary:test'],
        at_least=1,
    )

    for metric in OPTIONAL_METRICS:
        aggregator.assert_metric(metric, at_least=0)

    aggregator.assert_service_check("clickhouse.can_connect", count=1)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


def test_can_connect(aggregator, instance, dd_run_check):
    """
    Regression test: a copy of the `can_connect` service check must be submitted for each check run.
    (It used to be submitted only once on check init, which led to customer seeing "no data" in the UI.)
    """
    check = ClickhouseCheck('clickhouse', {}, [instance])

    # Test for consecutive healthy clickhouse.can_connect statuses
    num_runs = 3
    for _ in range(num_runs):
        dd_run_check(check)
    aggregator.assert_service_check("clickhouse.can_connect", count=num_runs, status=check.OK)
    aggregator.reset()

    # Test 1 healthy connection --> 2 Unhealthy service checks --> 1 healthy connection. Recovered
    dd_run_check(check)
    with mock.patch('clickhouse_driver.Client', side_effect=NetworkError('Connection refused')):
        with mock.patch('datadog_checks.clickhouse.ClickhouseCheck.ping_clickhouse', return_value=False):
            with pytest.raises(Exception):
                dd_run_check(check)
            with pytest.raises(Exception):
                dd_run_check(check)
    dd_run_check(check)
    aggregator.assert_service_check("clickhouse.can_connect", count=2, status=check.CRITICAL)
    aggregator.assert_service_check("clickhouse.can_connect", count=2, status=check.OK)
    aggregator.reset()

    # Test Exception in ping_clickhouse(), but reestablishes connection.
    dd_run_check(check)
    with mock.patch('datadog_checks.clickhouse.ClickhouseCheck.ping_clickhouse', side_effect=Error()):
        # connect() should be able to handle an exception in ping_clickhouse() and attempt reconnection
        dd_run_check(check)
    dd_run_check(check)
    aggregator.assert_service_check("clickhouse.can_connect", count=3, status=check.OK)


def test_custom_queries(aggregator, instance, dd_run_check):
    instance['custom_queries'] = [
        {
            'tags': ['test:clickhouse'],
            'query': 'SELECT COUNT(*) FROM system.settings WHERE changed',
            'columns': [{'name': 'settings.changed', 'type': 'gauge'}],
        }
    ]

    check = ClickhouseCheck('clickhouse', {}, [instance])
    dd_run_check(check)

    aggregator.assert_metric(
        'clickhouse.settings.changed',
        metric_type=0,
        tags=[
            'server:{}'.format(instance['server']),
            'port:{}'.format(instance['port']),
            'db:default',
            'foo:bar',
            'test:clickhouse',
        ],
    )


@pytest.mark.skipif(CLICKHOUSE_VERSION == 'latest', reason='Version `latest` is ever-changing, skipping')
def test_version_metadata(instance, datadog_agent, dd_run_check):
    check = ClickhouseCheck('clickhouse', {}, [instance])
    check.check_id = 'test:123'
    dd_run_check(check)

    datadog_agent.assert_metadata(
        'test:123', {'version.scheme': 'calver', 'version.year': CLICKHOUSE_VERSION.split(".")[0]}
    )
