# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
from nose.plugins.attrib import attr
from mock import patch
from os.path import join, dirname

# project
from tests.checks.common import AgentCheckTest, Fixtures

FIXTURE_DIR = join(dirname(__file__), 'ci')
CASSANDRA_CONTAINER_NAME = 'dd-test-cassandra'

def mock_output(*args):
    return Fixtures.read_file('nodetool_output', sdk_dir=FIXTURE_DIR), "", 0

class TestCassandraNodetoolCheck(AgentCheckTest):
    """Basic Test for cassandra_check integration."""
    CHECK_NAME = 'cassandra_nodetool'

    config = {
        'instances': [
            {
                'nodetool': 'docker exec %s nodetool' % CASSANDRA_CONTAINER_NAME,
                'keyspaces': ['system', 'test'],
                'username': 'controlRole',
                'password': 'QED',
                'tags': ['foo', 'bar']
            }
        ]
    }

    @patch('utils.subprocess_output.get_subprocess_output', side_effect=mock_output)
    def test_check(self, mock_output):

        self.run_check(self.config)

        # test per datacenter metrics
        self.assertEquals(mock_output.call_args[0][0],
                          ['docker', 'exec', CASSANDRA_CONTAINER_NAME, 'nodetool', '-h', 'localhost', '-p',
                          '7199', '-u', 'controlRole', '-pw', 'QED', 'status', '--', 'test'])
        self.assertMetric('cassandra.nodetool.status.replication_availability', value=64.5,
                          tags=['keyspace:test', 'datacenter:dc1', 'foo', 'bar'])
        self.assertMetric('cassandra.nodetool.status.replication_availability', value=200,
                          tags=['keyspace:test', 'datacenter:dc2', 'foo', 'bar'])
        self.assertMetric('cassandra.nodetool.status.replication_factor', value=1,
                          tags=['keyspace:test', 'datacenter:dc1', 'foo', 'bar'])
        self.assertMetric('cassandra.nodetool.status.replication_factor', value=2,
                          tags=['keyspace:test', 'datacenter:dc2', 'foo', 'bar'])
        # test per node metrics
        tags = ['datacenter:dc2', 'node_id:e521a2a4-39d3-4311-a195-667bf56450f4',
                'node_address:172.21.0.4', 'rack:RAC1', 'foo', 'bar']
        self.assertMetric('cassandra.nodetool.status.status', value=1, tags=tags)
        self.assertMetric('cassandra.nodetool.status.owns', value=100, tags=tags + ['keyspace:test'])
        self.assertMetric('cassandra.nodetool.status.load', value=223340, tags=tags)
        self.assertServiceCheckOK('cassandra.nodetool.node_up', count=4)
        self.assertServiceCheckCritical('cassandra.nodetool.node_up', count=1)

    @attr(requires='cassandra_nodetool')
    def test_integration(self):
        self.run_check(self.config)

        self.assertMetric('cassandra.nodetool.status.replication_availability', value=200,
                          tags=['keyspace:test', 'datacenter:datacenter1', 'foo', 'bar'])
        self.assertMetric('cassandra.nodetool.status.replication_factor', value=2,
                          tags=['keyspace:test', 'datacenter:datacenter1', 'foo', 'bar'])
