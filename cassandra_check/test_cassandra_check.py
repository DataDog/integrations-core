# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
from nose.plugins.attrib import attr

# 3p
from cassandra.cluster import Cluster

# project
from tests.checks.common import AgentCheckTest


@attr(requires='cassandra_check')
class TestCassandraCheck(AgentCheckTest):
    """Basic Test for cassandra_check integration."""
    CHECK_NAME = 'cassandra_check'

    def test_check(self):

        # Create a keyspace with replication factor 2
        cluster = Cluster(connect_timeout=1)
        session = cluster.connect()
        session.execute("CREATE KEYSPACE IF NOT EXISTS test WITH REPLICATION = {'class': 'SimpleStrategy', 'replication_factor': 2}")
        cluster.shutdown()

        config = {
            'instances': [
                {'host': '127.0.0.1',
                'port': 9042,
                'keyspaces': ['test'],
                'tags': ['foo','bar'],
                'connect_timeout': 1}
            ]
        }

        self.run_check(config)
        # We should have the value 1 since the driver won't be able to connect to one of the container (port not exposed)
        self.assertMetric('cassandra.replication_failures', value=1, tags=['keyspace:test', 'cluster:Test Cluster', 'foo', 'bar'])
        self.assertServiceCheckOK('cassandra.can_connect', tags=['foo', 'bar'])
        # Raises when COVERAGE=true and coverage < 100%
        self.coverage_report()
