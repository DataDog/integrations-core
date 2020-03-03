# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

METRICS = (
    'hazelcast.mc.license_expiration_time',
    'hazelcast.instance.managed_executor_service.completed_task_count',
    'hazelcast.instance.managed_executor_service.is_shutdown',
    'hazelcast.instance.managed_executor_service.is_terminated',
    'hazelcast.instance.managed_executor_service.maximum_pool_size',
    'hazelcast.instance.managed_executor_service.pool_size',
    'hazelcast.instance.managed_executor_service.queue_size',
    'hazelcast.instance.managed_executor_service.remaining_queue_capacity',
    'hazelcast.instance.member_count',
    'hazelcast.instance.partition_service.active_partition_count',
    'hazelcast.instance.partition_service.is_cluster_safe',
    'hazelcast.instance.partition_service.is_local_member_safe',
    'hazelcast.instance.partition_service.partition_count',
    'hazelcast.instance.running',
    'hazelcast.instance.version',
    'jvm.buffer_pool.direct.capacity',
    'jvm.buffer_pool.direct.count',
    'jvm.buffer_pool.direct.used',
    'jvm.buffer_pool.mapped.capacity',
    'jvm.buffer_pool.mapped.count',
    'jvm.buffer_pool.mapped.used',
    'jvm.cpu_load.process',
    'jvm.cpu_load.system',
    'jvm.gc.cms.count',
    'jvm.gc.eden_size',
    'jvm.gc.old_gen_size',
    'jvm.gc.parnew.time',
    'jvm.gc.survivor_size',
    'jvm.heap_memory',
    'jvm.heap_memory_committed',
    'jvm.heap_memory_init',
    'jvm.heap_memory_max',
    'jvm.loaded_classes',
    'jvm.non_heap_memory',
    'jvm.non_heap_memory_committed',
    'jvm.non_heap_memory_init',
    'jvm.non_heap_memory_max',
    'jvm.os.open_file_descriptors',
    'jvm.thread_count',
)


@pytest.mark.e2e
def test(dd_agent_check):
    instance = {}
    aggregator = dd_agent_check(instance, rate=True)

    for metric in METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()
