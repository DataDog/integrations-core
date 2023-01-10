# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy

import mock
import pytest

from datadog_checks.aerospike import AerospikeCheck

from . import common

pytestmark = pytest.mark.unit


def test_datacenter_metrics(aggregator, dd_run_check):
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
    check._client.get_node_names = mock.MagicMock(
        side_effect=lambda: [{'address': common.HOST, 'port': common.PORT, 'node_name': 'test'}]
    )
    check.get_namespaces = mock.MagicMock()
    check.collect_info = mock.MagicMock()
    check.collect_throughput = mock.MagicMock()
    check.collect_latency = mock.MagicMock()
    dd_run_check(check)
    for metric in common.DATACENTER_METRICS:
        aggregator.assert_metric(metric)


def test_xdr_metrics(aggregator):
    check = AerospikeCheck('aerospike', {}, [common.INSTANCE])
    check.get_info = mock.MagicMock(
        return_value="lag=0;in_queue=0;in_progress=0;success=0;abandoned=0;not_found=0;filtered_out=0;"
        "retry_no_node=0;retry_conn_reset=0;retry_dest=0;recoveries=0;recoveries_pending=0;hot_keys=0;"
        "uncompressed_pct=0.000;compression_ratio=1.000;nodes=0;throughput=0;latency_ms=0;lap_us=1"
    )
    check.collect_xdr()

    for metric in common.XDR_DC_METRICS:
        aggregator.assert_metric(metric, tags=['datacenter:test'])


def test_multiple_xdr_metrics(aggregator):
    check = AerospikeCheck('aerospike', {}, [common.INSTANCE])
    check.get_info = mock.MagicMock(
        return_value="ip-10-10-17-247.ec2.internal:3000 (10.10.17.247) returned:\nlag=0;in_queue=0;in_progress=0;"
        "success=98344698;abandoned=0;not_found=0;filtered_out=0;retry_no_node=0;retry_conn_reset=775483;"
        "retry_dest=0;recoveries=293;recoveries_pending=0;hot_keys=20291210;uncompressed_pct=0.000;"
        "compression_ratio=1.000;throughput=0;latency_ms=17;lap_us=348    \n\nip-10-10-17-144.ec2.internal"
        ":3000 (10.10.17.144) returned:\nlag=0;in_queue=0;in_progress=0;success=98294822;abandoned=0;"
        "not_found=0;filtered_out=0;retry_no_node=0;retry_conn_reset=813513;retry_dest=0;recoveries=293;"
        "recoveries_pending=0;hot_keys=20286479;uncompressed_pct=0.000;compression_ratio=1.000;"
        "throughput=0;latency_ms=14;lap_us=232\n\n"
    )
    check.collect_xdr()
    for host in ['ip-10-10-17-247.ec2.internal', 'ip-10-10-17-144.ec2.internal']:
        for metric in common.XDR_DC_METRICS:
            aggregator.assert_metric(
                metric, tags=['datacenter:test', 'remote_dc_port:3000', 'remote_dc_host:{}'.format(host)]
            )


def test_collect_xdr_invalid_data(aggregator):
    check = AerospikeCheck('aerospike', {}, [common.INSTANCE])
    check.log = mock.MagicMock()
    with mock.patch('datadog_checks.aerospike.AerospikeCheck.get_info', return_value="ERROR::XDR-not-configured"):
        check.collect_xdr()
        check.log.debug.assert_called_with('Error collecting XDR metrics: %s', 'ERROR::XDR-not-configured')

    aggregator.assert_all_metrics_covered()  # no metric


def test_connection_uses_tls():
    instance = copy.deepcopy(common.INSTANCE)
    tls_config = {'cafile': 'my-ca-file', 'certfile': 'my-certfile', 'keyfile': 'my-keyfile'}
    instance['tls_config'] = copy.deepcopy(tls_config)

    check = AerospikeCheck('aerospike', {}, [instance])
    tls_config['enable'] = True

    assert check._tls_config == tls_config

    with mock.patch('aerospike.client') as client:
        check.get_client()
        assert client.assert_called_with({'host': [check._host], 'tls': tls_config})


@pytest.mark.parametrize(
    "return_vals",
    [
        pytest.param(
            [
                'error-no-data-yet-or-back-too-small',
                'batch-index:11:53:47-GMT,ops/sec,>1ms,>8ms,>64ms',
                '11:53:57,0.0,0.00,0.00,0.00',
                '{ns-1}-read:11:53:47-GMT,ops/sec,>1ms,>8ms,>64ms',
                '11:53:57,0.0,0.00,0.00,0.00',
                '{ns-1}-write:11:53:47-GMT,ops/sec,>1ms,>8ms,>64ms',
                '11:53:57,0.0,0.00,0.00,0.00',
                'BAD_LINE',
                '{ns-2_foo}-read:11:53:47-GMT,ops/sec,>1ms,>8ms,>64ms',
                '11:53:57,0.0,0.00,0.00,0.00',
                '{ns-2_foo}-write:11:53:47-GMT,ops/sec,>1ms,>8ms,>64ms',
                '11:53:57,0.0,0.00,0.00,0.00',
                'error-no-data-yet-or-back-too-small',
                'error-no-data-yet-or-back-too-small',
            ],
            id="Last value no data",
        ),
        pytest.param(
            [
                'error-no-data-yet-or-back-too-small',
                'batch-index:11:53:47-GMT,ops/sec,>1ms,>8ms,>64ms',
                '11:53:57,0.0,0.00,0.00,0.00',
                '{ns-1}-read:11:53:47-GMT,ops/sec,>1ms,>8ms,>64ms',
                '11:53:57,0.0,0.00,0.00,0.00',
                'BAD_LINE',
                '{ns-1}-write:11:53:47-GMT,ops/sec,>1ms,>8ms,>64ms',
                '11:53:57,0.0,0.00,0.00,0.00',
                '{ns-2_foo}-read:11:53:47-GMT,ops/sec,>1ms,>8ms,>64ms',
                '11:53:57,0.0,0.00,0.00,0.00',
                '{ns-2_foo}-write:11:53:47-GMT,ops/sec,>1ms,>8ms,>64ms',
                '11:53:57,0.0,0.00,0.00,0.00',
            ],
            id="Last value has data",
        ),
    ],
)
def test_collect_latency_parser(aggregator, return_vals):
    check = AerospikeCheck('aerospike', {}, [common.INSTANCE])
    check.get_info = mock.MagicMock(return_value=return_vals)
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

    for metric in (m for m in common.LAZY_METRICS if "write" in m):
        aggregator.assert_metric(metric, tags=['namespace:ns-2', 'tag:value'])

    aggregator.assert_all_metrics_covered()  # no metric


def test_collect_empty_data(aggregator):
    check = AerospikeCheck('aerospike', {}, [common.INSTANCE])

    check._client = mock.MagicMock()
    check._client.info_single_node.return_value = 'sets/test/ci	'  # from real data, there is a tab after the command
    check.log = mock.MagicMock()
    assert [] == check.get_info('sets/test/ci')


@pytest.mark.parametrize(
    "return_vals",
    [
        pytest.param(
            [
                'batch-index:',
                '{test}-read:msec,1.5,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,'
                '0.00',
                '{test}-write:',
                '{test}-pi-query:msec,1.5,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,'
                '0.00,0.00',
                '{test}-si-query:',
                'BAD_LINE',
                '{test}-udf:msec,1.7,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,'
                '0.00',
                '{test}-query:',
            ],
            id="Last value empty data",
        ),
        pytest.param(
            [
                'batch-index:',
                '{test}-read:msec,1.5,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,'
                '0.00',
                '{test}-write:',
                '{test}-pi-query:msec,1.5,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,'
                '0.00,0.00',
                '{test}-si-query:',
                'bad-line',
                '{test}-udf:msec,1.7,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,'
                '0.00',
            ],
            id="Last value has data",
        ),
    ],
)
def test_collect_latencies_parser(aggregator, return_vals):
    check = AerospikeCheck('aerospike', {}, [common.INSTANCE])
    check.get_info = mock.MagicMock(return_value=return_vals)

    check.collect_latencies(None)

    for metric_type in ['read', 'udf', 'pi_query']:
        for i in range(17):
            bucket = 2**i
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
