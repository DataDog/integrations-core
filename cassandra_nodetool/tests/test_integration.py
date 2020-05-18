# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import time

import pytest

from datadog_checks.cassandra_nodetool import CassandraNodetoolCheck

from . import common


@pytest.mark.integration
def test_integration(aggregator, dd_environment):
    """
    Testing Cassandra Nodetool Integration
    """
    integration = CassandraNodetoolCheck(common.CHECK_NAME, {}, [common.CONFIG_INSTANCE])
    # Starting with recent Cassandra versions, replication takes some time to
    # warm up, let's retry a few times.
    for _ in range(20):
        integration.check(common.CONFIG_INSTANCE)
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
