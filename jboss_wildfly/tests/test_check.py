# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    instance = {}
    aggregator = dd_agent_check(instance)
    metrics = [
        'jvm.non_heap_memory_max',
        'jboss.jdbc_preparedstatementcache.size',
        'jvm.heap_memory_committed',
        'jvm.gc.eden_size',
        'jboss.jdbc_xarecover.count',
        'jboss.transactions.aborted',
        'jvm.heap_memory',
        'jboss.transactions.resource_rollbacks',
        'jboss.jdbc_xacommit.count',
        'jvm.loaded_classes',
        'jvm.gc.parnew.time',
        'jboss.transactions.timed_out',
        'jboss.transactions.heuristics',
        'jboss.transactions.nested',
        'jboss.undertow_listener.request_count',
        'jboss.undertow_listener.error_count',
        'jboss.jdbc_connections.count',
        'jvm.cpu_load.system',
        'jvm.non_heap_memory_init',
        'jboss.transactions.inflight',
        'jvm.thread_count',
        'jvm.os.open_file_descriptors',
        'jboss.jdbc_preparedstatementcache.hit',
        'jvm.non_heap_memory',
        'jboss.transactions.system_rollbacks',
        'jboss.undertow_listener.bytes_received',
        'jboss.jdbc_connections.idle',
        'jboss.undertow_listener.processing_time',
        'jboss.transactions.application_rollbacks',
        'jvm.cpu_load.process',
        'jboss.undertow_listener.bytes_sent',
        'jboss.jdbc_xarollback.count',
        'jboss.transactions.committed',
        'jvm.gc.survivor_size',
        'jvm.non_heap_memory_committed',
        'jboss.jdbc_preparedstatementcache.miss',
        'jboss.jdbc_connections.active',
        'jboss.transactions.count',
        'jvm.heap_memory_init',
        'jvm.heap_memory_max',
        'jboss.jdbc_connections.request_wait',
        'jvm.gc.cms.count',
    ]
    for metric in metrics:
        aggregator.assert_metric(metric)

    tags = ['instance:jboss_wildfly']
    # TODO: Assert the status "status=AgentCheck.OK"
    # JMXFetch is currently sending the service check status as string, but should be number.
    # Add "status=AgentCheck.OK" once that's fixed
    # See https://github.com/DataDog/jmxfetch/pull/287
    aggregator.assert_service_check('jboss.can_connect', tags=tags)
