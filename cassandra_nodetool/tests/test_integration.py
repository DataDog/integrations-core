# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.cassandra_nodetool import CassandraNodetoolCheck

from . import common


@pytest.mark.integration
def test_integration(aggregator, dd_environment):
    """
    Testing Cassandra Nodetool Integration
    """
    integration = CassandraNodetoolCheck(common.CHECK_NAME, {}, {})
    integration.check(common.CONFIG_INSTANCE)

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
