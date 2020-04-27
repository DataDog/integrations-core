# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.dev.utils import get_metadata_metrics

JVM_METRICS = [
    "jvm.thread_count",
    "jvm.gc.cms.count",
    "jvm.gc.parnew.time",
    "jvm.buffer_pool.mapped.count",
    "jvm.buffer_pool.mapped.capacity",
    "jvm.buffer_pool.mapped.used",
    "jvm.gc.cms.count",
    "jvm.gc.parnew.time",
    "jvm.gc.survivor_size",
    "jvm.gc.old_gen_size",
    "jvm.buffer_pool.direct.count",
    "jvm.buffer_pool.direct.capacity",
    "jvm.buffer_pool.direct.used",
    "jvm.os.open_file_descriptors",
    "jvm.cpu_load.system",
    "jvm.cpu_load.process",
    "jvm.loaded_classes",
    "jvm.gc.eden_size",
    "jvm.heap_memory_init",
    "jvm.heap_memory_committed",
    "jvm.heap_memory_max",
    "jvm.heap_memory",
    "jvm.non_heap_memory_init",
    "jvm.non_heap_memory_committed",
    "jvm.non_heap_memory_max",
    "jvm.non_heap_memory",
]

@pytest.mark.e2e
def test_e2e(dd_agent_check):
    instance = {}
    aggregator = dd_agent_check(instance)  # type: AggregatorStub
    metrics = [
        "solr.searcher.maxdocs",
        "solr.searcher.numdocs",
        "solr.searcher.warmup",
    ]
    for metric in metrics + JVM_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), exclude=JVM_METRICS)
