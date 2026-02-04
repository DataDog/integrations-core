# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .common import CLICKHOUSE_VERSION
from .metrics import OPTIONAL_METRICS, get_metrics

pytestmark = pytest.mark.e2e


def test_check(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)
    server_tag = 'server:{}'.format(instance['server'])
    port_tag = 'port:{}'.format(instance['port'])
    metrics = get_metrics(CLICKHOUSE_VERSION)

    for metric in metrics:
        aggregator.assert_metric_has_tag(metric, server_tag, at_least=1)
        aggregator.assert_metric_has_tag(metric, port_tag, at_least=1)
        aggregator.assert_metric_has_tag(metric, 'db:default', at_least=1)
        aggregator.assert_metric_has_tag(metric, 'foo:bar', at_least=1)

    for metric in OPTIONAL_METRICS:
        aggregator.assert_metric(metric, at_least=0)

    aggregator.assert_metric(
        'clickhouse.dictionary.item.current',
        tags=[server_tag, port_tag, 'db:default', 'foo:bar', 'dictionary:test'],
        at_least=1,
    )

    for metric in OPTIONAL_METRICS:
        aggregator.assert_metric(metric, at_least=0)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_custom_queries_readonly_blocks_writes(dd_agent_check, instance):
    """Test that custom queries cannot execute write operations due to read-only mode."""
    # Add custom_query with write operation to instance config
    instance['custom_queries'] = [
        {
            'query': 'CREATE TABLE test_readonly (id UInt32) ENGINE = Memory',
            'columns': [],
            'tags': ['test:readonly'],
        }
    ]

    # Run check - should fail with read-only error
    with pytest.raises(Exception) as exc_info:
        dd_agent_check(instance)

    # Verify error message indicates read-only violation
    error_msg = str(exc_info.value).lower()
    assert 'readonly' in error_msg or 'read-only' in error_msg or 'read only' in error_msg, (
        f"Expected read-only error but got: {exc_info.value}"
    )
