# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.aerospike import AerospikeCheck


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
def test_check(aggregator, instance):
    check = AerospikeCheck('aerospike', {}, [instance])
    check.check(instance)
    _test_check(aggregator)


@pytest.mark.e2e
def test_e2e(dd_agent_check, instance):
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
    aggregator.assert_all_metrics_covered()

    aggregator.assert_service_check('aerospike.can_connect', AerospikeCheck.OK)
    aggregator.assert_service_check('aerospike.cluster_up', AerospikeCheck.OK)
