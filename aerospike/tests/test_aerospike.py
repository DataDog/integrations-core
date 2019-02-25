# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.aerospike import AerospikeCheck


@pytest.mark.usefixtures('dd_environment')
def test_check(aggregator, instance):
    check = AerospikeCheck('aerospike', {}, {})
    check.check(instance)

    # This hasn't been working
    # aggregator.assert_metric('aerospike.batch_error', 0)

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

    aggregator.assert_service_check('aerospike.cluster_up', check.OK)
