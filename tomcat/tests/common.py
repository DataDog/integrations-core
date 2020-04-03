# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from datadog_checks.dev import get_here

CHECK_NAME = "tomcat"

HERE = get_here()

"""
Metrics that are not produced by our e2e tests:
    "tomcat.cache.access_count",
    "tomcat.cache.hits_count",
"""


TOMCAT_E2E_METRICS = [
    # Tomcat
    "tomcat.max_time",
    "tomcat.threads.busy",
    "tomcat.threads.count",
    "tomcat.threads.max",
    # Rates
    "tomcat.bytes_sent",
    "tomcat.bytes_rcvd",
    "tomcat.error_count",
    "tomcat.request_count",
    "tomcat.processing_time",
    "tomcat.servlet.processing_time",
    "tomcat.servlet.error_count",
    "tomcat.servlet.request_count",
    "tomcat.jsp.count",
    "tomcat.jsp.reload_count",
    # JVM
    "jvm.buffer_pool.direct.capacity",
    "jvm.buffer_pool.direct.count",
    "jvm.buffer_pool.direct.used",
    "jvm.buffer_pool.mapped.capacity",
    "jvm.buffer_pool.mapped.count",
    "jvm.buffer_pool.mapped.used",
    "jvm.cpu_load.process",
    "jvm.cpu_load.system",
    "jvm.gc.cms.count",
    "jvm.gc.eden_size",
    "jvm.gc.old_gen_size",
    "jvm.gc.parnew.time",
    "jvm.gc.survivor_size",
    "jvm.heap_memory",
    "jvm.heap_memory_committed",
    "jvm.heap_memory_init",
    "jvm.heap_memory_max",
    "jvm.loaded_classes",
    "jvm.non_heap_memory",
    "jvm.non_heap_memory_committed",
    "jvm.non_heap_memory_init",
    "jvm.non_heap_memory_max",
    "jvm.os.open_file_descriptors",
    "jvm.thread_count",
]
