# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    instance = {}
    aggregator = dd_agent_check(instance)
    metrics = [
        "solr.searcher.maxdocs",
        "solr.searcher.numdocs",
        "solr.searcher.warmup",
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
    for metric in metrics:
        aggregator.assert_metric(metric)
