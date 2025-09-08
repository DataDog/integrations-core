# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .common import CLICKHOUSE_VERSION
from .metrics import get_metrics, get_optional_metrics


@pytest.mark.e2e
def test_check(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)
    server_tag = 'server:{}'.format(instance['server'])
    port_tag = 'port:{}'.format(instance['port'])
    metrics = get_metrics(CLICKHOUSE_VERSION)

    for metric in metrics:
        aggregator.assert_metric_has_tags(metric, [port_tag, server_tag, 'db:default', 'foo:bar'], at_least=1)

    for metric in get_optional_metrics(CLICKHOUSE_VERSION):
        aggregator.assert_metric(metric, at_least=0)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.e2e
def test_system_errors(dd_agent_check, instance, clickhouse_client):
    aggregator = dd_agent_check(instance, rate=True)

    aggregator.assert_metric('clickhouse.ClickHouseErrors_UNKNOWN_IDENTIFIER', at_least=0)

    with pytest.raises(Exception):
        clickhouse_client.execute('SELECT unknown')

    aggregator.assert_metric('clickhouse.ClickHouseErrors_UNKNOWN_IDENTIFIER', at_least=1)
