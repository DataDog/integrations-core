# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.clickhouse import ClickhouseCheck
from datadog_checks.dev.utils import get_metadata_metrics

from . import common
from .common import CLICKHOUSE_VERSION

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]


def test_check(aggregator, instance, dd_run_check):
    check = ClickhouseCheck('clickhouse', {}, [instance])
    dd_run_check(check)
    server_tag = 'server:{}'.format(instance['server'])
    port_tag = 'port:{}'.format(instance['port'])
    metrics = common.get_metrics(CLICKHOUSE_VERSION)

    for metric in metrics:
        aggregator.assert_metric_has_tags(metric, [port_tag, server_tag, 'db:default', 'foo:bar'], at_least=1)

    for metric in common.get_optional_metrics(CLICKHOUSE_VERSION):
        aggregator.assert_metric(metric, at_least=0)

    aggregator.assert_service_check("clickhouse.can_connect", count=1)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


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
