# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time

import mock
import pytest

from datadog_checks.aerospike import AerospikeCheck
from datadog_checks.base.utils.platform import Platform

LAZY_METRICS = [
    'aerospike.namespace.latency.write_over_64ms',
    'aerospike.namespace.latency.write_over_8ms',
    'aerospike.namespace.latency.write_over_1ms',
    'aerospike.namespace.latency.write_ops_sec',
    'aerospike.namespace.latency.read_over_64ms',
    'aerospike.namespace.latency.read_over_8ms',
    'aerospike.namespace.latency.read_over_1ms',
    'aerospike.namespace.latency.read_ops_sec',
    'aerospike.namespace.tps.read',
]


@pytest.mark.skipif(not Platform.is_linux(), reason='Aerospike client only installs on Linux for version == 3.10')
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
def test_check(aggregator, instance):
    check = AerospikeCheck('aerospike', {}, [instance])
    # sleep to make sure client is available
    time.sleep(30)
    for _ in range(10):
        check.check(instance)
        time.sleep(1)
    _test_check(aggregator)


@pytest.mark.skipif(not Platform.is_linux(), reason='Aerospike client only installs on Linux for version == 3.10')
def test_version_metadata(aggregator, instance, datadog_agent):

    check = AerospikeCheck('aerospike', {}, [instance])
    check.check_id = 'test:123'

    # sleep to make sure client is available
    time.sleep(30)
    for _ in range(10):
        check.check(instance)
        time.sleep(1)

    raw_version = check.get_info("build")[0]
    major, minor = raw_version.split('.')[:2]
    version_metadata = {
        'version.scheme': 'semver',
        'version.major': major,
        'version.minor': minor,
        'version.patch': mock.ANY,
        'version.raw': raw_version,
    }

    datadog_agent.assert_metadata('test:123', version_metadata)


@pytest.mark.e2e
def test_e2e(dd_agent_check, instance, init_db):
    aggregator = dd_agent_check(instance)

    _test_check(aggregator)


def _test_check(aggregator):
    aggregator.assert_metric('aerospike.cluster_size')
    aggregator.assert_metric('aerospike.namespace.objects')
    aggregator.assert_metric('aerospike.namespace.hwm_breached')
    aggregator.assert_metric('aerospike.namespace.client_write_error', 0)
    aggregator.assert_metric('aerospike.namespace.client_write_success', 1)
    aggregator.assert_metric('aerospike.namespace.truncate_lut', 0)
    aggregator.assert_metric('aerospike.namespace.tombstones', 0)
    aggregator.assert_metric('aerospike.set.tombstones', 0)
    aggregator.assert_metric('aerospike.set.truncate_lut', 0)
    aggregator.assert_metric('aerospike.set.memory_data_bytes', 289)
    aggregator.assert_metric('aerospike.set.objects', 1, tags=['namespace:test', 'set:characters', 'tag:value'])
    aggregator.assert_metric(
        'aerospike.set.stop_writes_count', 0, tags=['namespace:test', 'set:characters', 'tag:value']
    )

    for metric in LAZY_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_metric('aerospike.namespace.tps.write', at_least=0)
    aggregator.assert_all_metrics_covered()

    aggregator.assert_service_check('aerospike.can_connect', AerospikeCheck.OK)
    aggregator.assert_service_check('aerospike.cluster_up', AerospikeCheck.OK)
