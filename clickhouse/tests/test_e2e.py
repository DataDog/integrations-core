# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from .metrics import ALL_METRICS

pytestmark = pytest.mark.e2e


def test_check(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)

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
