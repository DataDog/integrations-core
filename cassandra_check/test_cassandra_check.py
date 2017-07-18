# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
from nose.plugins.attrib import attr
from mock import patch
from os.path import join, dirname

# project
from tests.checks.common import AgentCheckTest, Fixtures

FIXTURE_DIR = join(dirname(__file__), 'ci')

@attr(requires='cassandra_check')
class TestCassandraCheck(AgentCheckTest):
    """Basic Test for cassandra_check integration."""
    CHECK_NAME = 'cassandra_check'

    config = {
        'instances': [
            {
                'host': 'localhost',
                'keyspaces': ['test'],
                'tags': ['foo', 'bar']
            }
        ]
    }

    @patch('_cassandra_check.get_subprocess_output',
           return_value=Fixtures.read_file('nodetool_output', sdk_dir=FIXTURE_DIR))
    def test_check(self, mock_output):

        self.run_check(self.config)

        mock_output.assertCalledWith(['/usr/bin/nodetool', '-h', 'localhost', '-p', '7199', '--', 'test'])
        self.assertMetric('cassandra.replication_availability', value=64.5,
                          tags=['keyspace:test', 'datacenter:dc1', 'foo', 'bar'])
        self.assertMetric('cassandra.replication_availability', value=100,
                          tags=['keyspace:test', 'datacenter:dc2', 'foo', 'bar'])
        self.assertMetric('cassandra.replication_factor', value=1,
                          tags=['keyspace:test', 'datacenter:dc1', 'foo', 'bar'])
        self.assertMetric('cassandra.replication_factor', value=2,
                          tags=['keyspace:test', 'datacenter:dc2', 'foo', 'bar'])

        self.coverage_report()
