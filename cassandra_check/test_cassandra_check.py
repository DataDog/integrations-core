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

def mock_output(*args):
    return Fixtures.read_file('nodetool_output', sdk_dir=FIXTURE_DIR), "", 0

class TestCassandraCheck(AgentCheckTest):
    """Basic Test for cassandra_check integration."""
    CHECK_NAME = 'cassandra_check'

    config = {
        'instances': [
            {
                'host': 'localhost',
                'keyspaces': ['test'],
                'username': 'controlRole',
                'password': 'QED',
                'tags': ['foo', 'bar']
            }
        ]
    }

    @patch('utils.subprocess_output.get_subprocess_output', side_effect=mock_output)
    def test_check(self, mock_output):

        self.run_check(self.config)

        self.assertEquals(mock_output.call_args[0][0],
                          ['/usr/bin/nodetool', '-h', 'localhost', '-p', '7199', '-u',
                          'controlRole', '-pw', 'QED', 'status', '--', 'test'])
        self.assertMetric('cassandra.replication_availability', value=64.5,
                          tags=['keyspace:test', 'datacenter:dc1', 'foo', 'bar'])
        self.assertMetric('cassandra.replication_availability', value=200,
                          tags=['keyspace:test', 'datacenter:dc2', 'foo', 'bar'])
        self.assertMetric('cassandra.replication_factor', value=1,
                          tags=['keyspace:test', 'datacenter:dc1', 'foo', 'bar'])
        self.assertMetric('cassandra.replication_factor', value=2,
                          tags=['keyspace:test', 'datacenter:dc2', 'foo', 'bar'])

        self.coverage_report()

    @attr(requires='cassandra_check')
    def test_integration(self):
        self.run_check(self.config)

        self.assertMetric('cassandra.replication_availability', value=200,
                          tags=['keyspace:test', 'datacenter:datacenter1', 'foo', 'bar'])
        self.assertMetric('cassandra.replication_factor', value=2,
                          tags=['keyspace:test', 'datacenter:datacenter1', 'foo', 'bar'])
        self.coverage_report()
