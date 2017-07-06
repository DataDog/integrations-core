# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
from nose.plugins.attrib import attr
from mock import patch

# 3p
from cassandra.cluster import Cluster # pylint: disable=E0611
from cassandra.metadata import TokenMap # pylint: disable=E0611

# project
from tests.checks.common import AgentCheckTest

class MockHost:
    def __init__(self, up):
        self.is_up = up

def mock_get_replicas(self, keyspace, token):
    return [MockHost(True), MockHost(False)]

@attr(requires='cassandra_check')
class TestCassandraCheck(AgentCheckTest):
    """Basic Test for cassandra_check integration."""
    CHECK_NAME = 'cassandra_check'

    config = {
        'instances': [
            {'host': '127.0.0.1',
            'port': 9042,
            'keyspaces': ['test'],
            'tags': ['foo','bar'],
            'connect_timeout': 1}
        ]
    }

    def test_check(self):
        # Create a keyspace with replication factor 2
        cluster = Cluster(connect_timeout=1)
        session = cluster.connect()
        session.execute("CREATE KEYSPACE IF NOT EXISTS test WITH REPLICATION = {'class': 'SimpleStrategy', 'replication_factor': 2}")
        cluster.shutdown()
        # Run check with both, we should get the value 0 (on mac this will fail since
        # there is no docker0 bridge so the connection to the second container cannot be made)
        self.run_check(self.config)
        self.assertMetric('cassandra.replication_failures', value=0, tags=['keyspace:test', 'cluster:Test Cluster', 'foo', 'bar'])
        self.assertServiceCheckOK('cassandra.can_connect', tags=['foo', 'bar'])

        self.coverage_report()

    @patch.object(TokenMap, 'get_replicas', mock_get_replicas)
    def test_1_replica_down(self):
        # We should have the value 1 since the driver won't be able to connect to the second container
        self.run_check(self.config)
        self.assertMetric('cassandra.replication_failures', value=1, tags=['keyspace:test', 'cluster:Test Cluster', 'foo', 'bar'])
        self.assertServiceCheckOK('cassandra.can_connect', tags=['foo', 'bar'])

        self.coverage_report()
