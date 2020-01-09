# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import time

import pytest

from . import common


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    # Starting with recent Cassandra versions, replication takes some time to
    # warm up, let's retry a few times.
    for _ in range(20):
        aggregator = dd_agent_check(common.CONFIG_INSTANCE)
        try:
            aggregator.assert_metric(
                'cassandra.nodetool.status.replication_availability',
                value=200,
                tags=['keyspace:test', 'datacenter:datacenter1', 'foo', 'bar'],
            )
        except AssertionError:
            time.sleep(5)
        else:
            break

    aggregator.assert_metric(
        'cassandra.nodetool.status.replication_availability',
        value=200,
        tags=['keyspace:test', 'datacenter:datacenter1', 'foo', 'bar'],
    )

    aggregator.assert_metric(
        'cassandra.nodetool.status.replication_factor',
        value=2,
        tags=['keyspace:test', 'datacenter:datacenter1', 'foo', 'bar'],
    )

    aggregator.assert_metric('cassandra.nodetool.status.load')
    aggregator.assert_metric('cassandra.nodetool.status.owns', value=100)
    aggregator.assert_metric('cassandra.nodetool.status.status', value=1)
    aggregator.assert_all_metrics_covered()
