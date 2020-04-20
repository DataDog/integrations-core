# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .common import TOMCAT_E2E_METRICS

JVM_METRICS = [
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
    'jvm.heap_memory_committed',
    'jvm.heap_memory_init',
    'jvm.heap_memory_max',
    'jvm.heap_memory',
    'jvm.loaded_classes',
    'jvm.non_heap_memory_committed',
    'jvm.non_heap_memory_init',
    'jvm.non_heap_memory_max',
    'jvm.non_heap_memory',
    'jvm.os.open_file_descriptors',
    'jvm.thread_count',
]

COUNTER_METRICS = [
    # TODO: JMXFetch is not reporting in-app type for JMX `counter` type.
    #       Remove this exclusion list when fixed.
    'tomcat.bytes_rcvd',
    'tomcat.bytes_sent',
    'tomcat.error_count',
    'tomcat.jsp.count',
    'tomcat.jsp.reload_count',
    'tomcat.processing_time',
    'tomcat.request_count',
    'tomcat.servlet.error_count',
    'tomcat.servlet.processing_time',
    'tomcat.servlet.request_count',
    'tomcat.string_cache.access_count',
    'tomcat.string_cache.hit_count',
    'tomcat.web.cache.hit_count',
    'tomcat.web.cache.lookup_count',
]


@pytest.mark.e2e
def test(dd_agent_check):
    instance = {}
    aggregator = dd_agent_check(instance, rate=True)

    for metric in TOMCAT_E2E_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()

    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), exclude=JVM_METRICS + COUNTER_METRICS)
