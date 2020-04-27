# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from datadog_checks.dev import get_docker_hostname

HOST = get_docker_hostname()

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

SOLR_METRICS = [
    "solr.document_cache.evictions",
    "solr.document_cache.hits",
    "solr.document_cache.inserts",
    "solr.document_cache.lookups",
    "solr.filter_cache.evictions",
    "solr.filter_cache.hits",
    "solr.filter_cache.inserts",
    "solr.filter_cache.lookups",
    "solr.query_result_cache.evictions",
    "solr.query_result_cache.hits",
    "solr.query_result_cache.inserts",
    "solr.query_result_cache.lookups",
    "solr.search_handler.errors",
    "solr.search_handler.requests",
    "solr.search_handler.time",
    "solr.search_handler.timeouts",
    "solr.searcher.maxdocs",
    "solr.searcher.numdocs",
    "solr.searcher.warmup",
]
