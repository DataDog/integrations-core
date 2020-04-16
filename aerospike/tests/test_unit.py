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
    check.collect_version = mock.MagicMock()
    check.check(common.INSTANCE)
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

    metrics = [
        'aerospike.namespace.latency.read_ops_sec',
        'aerospike.namespace.latency.read_over_1ms',
        'aerospike.namespace.latency.read_over_8ms',
        'aerospike.namespace.latency.read_over_64ms',
        'aerospike.namespace.latency.write_ops_sec',
        'aerospike.namespace.latency.write_over_1ms',
        'aerospike.namespace.latency.write_over_8ms',
        'aerospike.namespace.latency.write_over_64ms',
    ]

    for ns in ['ns-1', 'ns-2_foo']:
        for metric in metrics:
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
