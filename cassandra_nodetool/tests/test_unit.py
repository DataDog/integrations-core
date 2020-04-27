# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from os import path

from mock import patch

from datadog_checks.cassandra_nodetool import CassandraNodetoolCheck

from . import common


def _read_fixture(filename):
    with open(path.join(common.HERE, 'fixtures', filename)) as f:
        contents = f.read()
        return contents, "", 0


def mock_output(*args, **kwargs):
    return _read_fixture('nodetool_output')


def mock_output_old_format(*args, **kwargs):
    return _read_fixture('nodetool_output_1.2')


@patch('datadog_checks.cassandra_nodetool.cassandra_nodetool.get_subprocess_output', side_effect=mock_output)
def test_check(mock_output, aggregator):
    _check(mock_output, aggregator)


@patch('datadog_checks.cassandra_nodetool.cassandra_nodetool.get_subprocess_output', side_effect=mock_output_old_format)
def test_check_old_format(mock_output, aggregator):
    _check(mock_output, aggregator)


def _check(mock_output, aggregator):
    integration = CassandraNodetoolCheck(common.CHECK_NAME, {}, [common.CONFIG_INSTANCE])
    integration.check(common.CONFIG_INSTANCE)

    # test per datacenter metrics
    args = [
        'docker',
        'exec',
        common.CASSANDRA_CONTAINER_NAME,
        'nodetool',
        '-h',
        'localhost',
        '-p',
        '7199',
        '-u',
        'controlRole',
        '-pw',
        'QED',
        'status',
        '--',
        'test',
    ]
    assert all([a == b for a, b in zip(mock_output.call_args[0][0], args)])
    aggregator.assert_metric(
        'cassandra.nodetool.status.replication_availability',
        value=64.5,
        tags=['keyspace:test', 'datacenter:dc1', 'foo', 'bar'],
    )
    aggregator.assert_metric(
        'cassandra.nodetool.status.replication_availability',
        value=200,
        tags=['keyspace:test', 'datacenter:dc2', 'foo', 'bar'],
    )
    aggregator.assert_metric(
        'cassandra.nodetool.status.replication_factor', value=1, tags=['keyspace:test', 'datacenter:dc1', 'foo', 'bar']
    )
    aggregator.assert_metric(
        'cassandra.nodetool.status.replication_factor', value=2, tags=['keyspace:test', 'datacenter:dc2', 'foo', 'bar']
    )
    # test per node metrics
    tags = [
        'datacenter:dc2',
        'node_id:e521a2a4-39d3-4311-a195-667bf56450f4',
        'node_address:172.21.0.4',
        'rack:RAC1',
        'foo',
        'bar',
    ]
    aggregator.assert_metric('cassandra.nodetool.status.status', value=1, tags=tags)
    aggregator.assert_metric('cassandra.nodetool.status.owns', value=100, tags=tags + ['keyspace:test'])
    aggregator.assert_metric('cassandra.nodetool.status.load', value=223340, tags=tags)
    aggregator.assert_service_check('cassandra.nodetool.node_up', status=CassandraNodetoolCheck.OK, count=4)
    aggregator.assert_service_check('cassandra.nodetool.node_up', status=CassandraNodetoolCheck.CRITICAL, count=1)

    # Assert coverage for this check on this instance
    aggregator.assert_all_metrics_covered()

    integration = CassandraNodetoolCheck(common.CHECK_NAME, {}, [common.CONFIG_INSTANCE])
    integration.check(common.CONFIG_INSTANCE)

    assert all(
        [
            a == b
            for a, b in zip(
                mock_output.call_args[0][0],
                [
                    'docker',
                    'exec',
                    common.CASSANDRA_CONTAINER_NAME,
                    'nodetool',
                    '-h',
                    'localhost',
                    '-p',
                    '7199',
                    '-u',
                    'controlRole',
                    '-pw',
                    'QED',
                    'status',
                    '--',
                    'test',
                ],
            )
        ]
    )
