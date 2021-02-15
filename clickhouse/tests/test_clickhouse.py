# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest
from clickhouse_driver.errors import Error, NetworkError

from datadog_checks.clickhouse import ClickhouseCheck

from .common import CLICKHOUSE_VERSION
from .metrics import ALL_METRICS

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]


def test_clickhouse(aggregator, instance):
    # We do not do aggregator.assert_all_metrics_covered() because depending on timing, some other metrics may appear
    check = ClickhouseCheck('clickhouse', {}, [instance])
    check.run()

    server_tag = 'server:{}'.format(instance['server'])
    port_tag = 'port:{}'.format(instance['port'])
    for metric in ALL_METRICS:
        aggregator.assert_metric_has_tag(metric, server_tag)
        aggregator.assert_metric_has_tag(metric, port_tag)
        aggregator.assert_metric_has_tag(metric, 'db:default')
        aggregator.assert_metric_has_tag(metric, 'foo:bar')

    aggregator.assert_metric('clickhouse.table.replicated.total', 2)
    aggregator.assert_metric(
        'clickhouse.dictionary.item.current', tags=[server_tag, port_tag, 'db:default', 'foo:bar', 'dictionary:test']
    )
    aggregator.assert_service_check("clickhouse.can_connect", count=1)


def test_can_connect(aggregator, instance):
    """
    Regression test: a copy of the `can_connect` service check must be submitted for each check run.
    (It used to be submitted only once on check init, which led to customer seeing "no data" in the UI.)
    """
    check = ClickhouseCheck('clickhouse', {}, [instance])

    # Test for consecutive healthy clickhouse.can_connect statuses
    num_runs = 3
    for _ in range(num_runs):
        check.run()
    aggregator.assert_service_check("clickhouse.can_connect", count=num_runs, status=check.OK)
    aggregator.reset()

    # Test 1 healthy connection --> 2 Unhealthy service checks --> 1 healthy connection. Recovered
    check.run()
    with mock.patch('clickhouse_driver.Client', side_effect=NetworkError('Connection refused')):
        with mock.patch('datadog_checks.clickhouse.ClickhouseCheck.ping_clickhouse', return_value=False):
            check.run()
            check.run()
    check.run()
    aggregator.assert_service_check("clickhouse.can_connect", count=2, status=check.CRITICAL)
    aggregator.assert_service_check("clickhouse.can_connect", count=2, status=check.OK)
    aggregator.reset()

    # Test Exception in ping_clickhouse(), but reestablishes connection.
    check.run()
    with mock.patch('datadog_checks.clickhouse.ClickhouseCheck.ping_clickhouse', side_effect=Error()):
        # connect() should be able to handle an exception in ping_clickhouse() and attempt reconnection
        check.run()
    check.run()
    aggregator.assert_service_check("clickhouse.can_connect", count=3, status=check.OK)


def test_custom_queries(aggregator, instance):
    instance['custom_queries'] = [
        {
            'tags': ['test:clickhouse'],
            'query': 'SELECT COUNT(*) FROM system.settings WHERE changed',
            'columns': [{'name': 'settings.changed', 'type': 'gauge'}],
        }
    ]

    check = ClickhouseCheck('clickhouse', {}, [instance])
    check.run()

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
def test_clickhouse_version_metadata(instance, datadog_agent):
    check = ClickhouseCheck('clickhouse', {}, [instance])
    check.check_id = 'test:123'
    check.run()

    datadog_agent.assert_metadata('test:123', {'version.scheme': 'calver', 'version.year': CLICKHOUSE_VERSION})
