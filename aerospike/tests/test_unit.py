# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy

import mock
import pytest

from datadog_checks.aerospike import AerospikeCheck

from . import common

pytestmark = pytest.mark.unit


def test_datacenter_metrics(aggregator):
    check = AerospikeCheck('aerospike', {}, [common.INSTANCE])
    original_get_info = check.get_info

    def mock_get_info(command, separator=";"):
        if command == 'dcs':
            return ['test']
        elif command.startswith("dc/"):
            return common.MOCK_DATACENTER_METRICS

        return original_get_info(command, separator)

    check.get_info = mock_get_info
    check._client = mock.MagicMock()
    check.get_namespaces = mock.MagicMock()
    check.collect_info = mock.MagicMock()
    check.collect_throughput = mock.MagicMock()
    check.collect_latency = mock.MagicMock()
    check.check(None)
    for metric in common.DATACENTER_METRICS:
        aggregator.assert_metric(metric)


def test_connection_uses_tls():
    instance = copy.deepcopy(common.INSTANCE)
    tls_config = {'cafile': 'my-ca-file', 'certfile': 'my-certfile', 'keyfile': 'my-keyfile'}
    instance['tls_config'] = copy.deepcopy(tls_config)

    check = AerospikeCheck('aerospike', {}, [instance])
    tls_config['enable'] = True

    assert check._tls_config == tls_config

    with mock.patch('aerospike.client') as client:
        check.get_client()
        assert client.called_with({'host': check._host, 'tls': tls_config})


def test_collect_latency_parser(aggregator):
    check = AerospikeCheck('aerospike', {}, [common.INSTANCE])
    check.get_info = mock.MagicMock(
        return_value=[
            'error-no-data-yet-or-back-too-small',
            'batch-index:11:53:47-GMT,ops/sec,>1ms,>8ms,>64ms',
            '11:53:57,0.0,0.00,0.00,0.00',
            '{ns-1}-read:11:53:47-GMT,ops/sec,>1ms,>8ms,>64ms',
            '11:53:57,0.0,0.00,0.00,0.00',
            '{ns-1}-write:11:53:47-GMT,ops/sec,>1ms,>8ms,>64ms',
            '11:53:57,0.0,0.00,0.00,0.00',
            '{ns-2_foo}-read:11:53:47-GMT,ops/sec,>1ms,>8ms,>64ms',
            '11:53:57,0.0,0.00,0.00,0.00',
            '{ns-2_foo}-write:11:53:47-GMT,ops/sec,>1ms,>8ms,>64ms',
            '11:53:57,0.0,0.00,0.00,0.00',
            'error-no-data-yet-or-back-too-small',
            'error-no-data-yet-or-back-too-small',
        ]
    )
    check.collect_latency(None)

    for ns in ['ns-1', 'ns-2_foo']:
        for metric in common.LAZY_METRICS:
            if "batch_index" in metric:
                aggregator.assert_metric(metric, tags=['tag:value'])
            else:
                aggregator.assert_metric(metric, tags=['namespace:{}'.format(ns), 'tag:value'])

    aggregator.assert_all_metrics_covered()


def test_collect_latency_invalid_data(aggregator):
    check = AerospikeCheck('aerospike', {}, [common.INSTANCE])
    check.get_info = mock.MagicMock(
        return_value=[
            'error-no-data-yet-or-back-too-small',
            'xxxread:11:53:47-GMT,ops/sec,>1ms,>8ms,>64ms',
            '11:53:57,0.0,0.00,0.00,0.00',
            '{ns-2}-write:11:53:47-GMT,ops/sec,>1ms,>8ms,>64ms',
            '11:53:57,0.0,0.00,0.00,0.00',
        ]
    )
    check.log = mock.MagicMock()
    check.collect_latency(None)

    check.log.warning.assert_called_with(
        'Invalid data. Namespace and/or metric name not found in line: `%s`',
        'xxxread:11:53:47-GMT,ops/sec,>1ms,>8ms,>64ms',
    )

    aggregator.assert_all_metrics_covered()  # no metric


def test_collect_empty_data(aggregator):
    check = AerospikeCheck('aerospike', {}, [common.INSTANCE])

    check._client = mock.MagicMock()
    check._client.info_node.return_value = 'sets/test/ci	'  # from real data, there is a tab after the command
    check.log = mock.MagicMock()
    assert [] == check.get_info('sets/test/ci')


def test_collect_latencies_parser(aggregator):
    check = AerospikeCheck('aerospike', {}, [common.INSTANCE])
    check.get_info = mock.MagicMock(
        return_value=[
            'batch-index:',
            '{test}-read:msec,1.5,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00',
            '{test}-write:',
            '{test}-udf:msec,1.7,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00',
            '{test}-query:',
        ]
    )
    check.collect_latencies(None)

    for metric_type in ['read', 'udf']:
        for i in range(17):
            bucket = 2 ** i
            aggregator.assert_metric(
                'aerospike.namespace.latency.{}'.format(metric_type),
                tags=['namespace:{}'.format('test'), 'tag:value', 'bucket:{}'.format(str(bucket))],
            )

        for n in [1, 8, 64]:
            aggregator.assert_metric(
                'aerospike.namespace.latency.{}_over_{}ms'.format(metric_type, str(n)),
                tags=['namespace:{}'.format('test'), 'tag:value', 'bucket:{}'.format(str(n))],
            )

        aggregator.assert_metric(
            'aerospike.namespace.latency.{}_ops_sec'.format(metric_type),
            tags=['namespace:{}'.format('test'), 'tag:value'],
        )
    aggregator.assert_all_metrics_covered()
