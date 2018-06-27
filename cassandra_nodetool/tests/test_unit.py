# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from mock import patch
from os import path
import common
from datadog_checks.cassandra_nodetool import CassandraNodetoolCheck


def mock_output(*args):
    with open(path.join(common.HERE, 'fixtures', 'nodetool_output')) as f:
        contents = f.read()
        return contents, "", 0


@patch('datadog_checks.cassandra_nodetool.cassandra_nodetool.get_subprocess_output', side_effect=mock_output)
def test_check(mock_output, aggregator):
    integration = CassandraNodetoolCheck(common.CHECK_NAME, {}, {})
    integration.check(common.CONFIG_INSTANCE)

    # test per datacenter metrics
    assert all([a == b for a, b in zip(mock_output.call_args[0][0],
                                       ['docker', 'exec', common.CASSANDRA_CONTAINER_NAME, 'nodetool', '-h',
                                        'localhost', '-p', '7199', '-u', 'controlRole', '-pw', 'QED',
                                        'status', '--', 'test']
                                       )
                ])
    aggregator.assert_metric('cassandra.nodetool.status.replication_availability', value=64.5,
                             tags=['keyspace:test', 'datacenter:dc1', 'foo', 'bar'])
    aggregator.assert_metric('cassandra.nodetool.status.replication_availability', value=200,
                             tags=['keyspace:test', 'datacenter:dc2', 'foo', 'bar'])
    aggregator.assert_metric('cassandra.nodetool.status.replication_factor', value=1,
                             tags=['keyspace:test', 'datacenter:dc1', 'foo', 'bar'])
    aggregator.assert_metric('cassandra.nodetool.status.replication_factor', value=2,
                             tags=['keyspace:test', 'datacenter:dc2', 'foo', 'bar'])
    # test per node metrics
    tags = ['datacenter:dc2', 'node_id:e521a2a4-39d3-4311-a195-667bf56450f4',
            'node_address:172.21.0.4', 'rack:RAC1', 'foo', 'bar']
    aggregator.assert_metric('cassandra.nodetool.status.status', value=1, tags=tags)
    aggregator.assert_metric('cassandra.nodetool.status.owns', value=100, tags=tags + ['keyspace:test'])
    aggregator.assert_metric('cassandra.nodetool.status.load', value=223340, tags=tags)
    aggregator.assert_service_check('cassandra.nodetool.node_up', status=CassandraNodetoolCheck.OK, count=4)
    aggregator.assert_service_check('cassandra.nodetool.node_up', status=CassandraNodetoolCheck.CRITICAL, count=1)

    # Assert coverage for this check on this instance
    aggregator.assert_all_metrics_covered()

    config_with_port = common.CONFIG_INSTANCE.copy()
    config_with_port['port'] = 7199
    integration = CassandraNodetoolCheck(common.CHECK_NAME, {}, {})
    integration.check(common.CONFIG_INSTANCE)

    assert all([a == b for a, b in zip(mock_output.call_args[0][0],
                                       ['docker', 'exec', common.CASSANDRA_CONTAINER_NAME, 'nodetool', '-h',
                                        'localhost', '-p', '7199', '-u', 'controlRole', '-pw', 'QED',
                                        'status', '--', 'test']
                                       )
                ])
