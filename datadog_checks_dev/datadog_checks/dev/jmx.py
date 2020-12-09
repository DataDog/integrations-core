# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

JVM_E2E_METRICS = [
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
    'jvm.gc.metaspace_size',
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
]

JMX_E2E_METRICS = [
    'jmx.gc.major_collection_count',
    'jmx.gc.major_collection_time',
    'jmx.gc.minor_collection_count',
    'jmx.gc.minor_collection_time',
]
