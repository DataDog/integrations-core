# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.clickhouse import ClickhouseCheck

from .common import CLICKHOUSE_VERSION
from .metrics import ALL_METRICS

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]


def test_check(aggregator, instance):
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
    num_runs = 3
    for _ in range(num_runs):
        check.run()
    aggregator.assert_service_check("clickhouse.can_connect", count=num_runs)


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
def test_version_metadata(instance, datadog_agent):
    check = ClickhouseCheck('clickhouse', {}, [instance])
    check.check_id = 'test:123'
    check.run()

    datadog_agent.assert_metadata('test:123', {'version.scheme': 'calver', 'version.year': CLICKHOUSE_VERSION})
