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


def connection_uses_tls():
    instance = copy.deepcopy(common.INSTANCE)
    tls_config = {'cafile': 'my-ca-file', 'certfile': 'my-certfile', 'keyfile': 'my-keyfile'}
    instance['tls_config'] = copy.deepcopy(tls_config)

    check = AerospikeCheck('aerospike', {}, [common.INSTANCE])
    tls_config['enable'] = True

    assert check._tls_config == tls_config

    with mock.patch('aerospike.client') as client:
        check.get_client()
        assert client.called_with({'host': check._host, 'tls': tls_config})
