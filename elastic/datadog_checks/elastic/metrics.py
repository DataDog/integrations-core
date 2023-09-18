# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from bisect import bisect

from .utils import byte_to_mebibyte, ms_to_second

# Metrics definition format is a dictionary mapping:
# datadog_metric_name --> (datadog_metric_type, es_metric_name, optional_conversion_func)

# Clusterwise metrics, pre aggregated on ES, compatible with all ES versions
PRIMARY_SHARD_METRICS = {
    'elasticsearch.primaries.docs.count': ('gauge', '_all.primaries.docs.count'),
    'elasticsearch.primaries.docs.deleted': ('gauge', '_all.primaries.docs.deleted'),
    'elasticsearch.primaries.store.size': ('gauge', '_all.primaries.store.size_in_bytes'),
    'elasticsearch.primaries.indexing.index.total': ('gauge', '_all.primaries.indexing.index_total'),
    'elasticsearch.primaries.indexing.index.time': (
        'gauge',
        '_all.primaries.indexing.index_time_in_millis',
        lambda ms: ms_to_second(ms),
    ),
    'elasticsearch.primaries.indexing.index.current': ('gauge', '_all.primaries.indexing.index_current'),
    'elasticsearch.primaries.indexing.delete.total': ('gauge', '_all.primaries.indexing.delete_total'),
    'elasticsearch.primaries.indexing.delete.time': (
        'gauge',
        '_all.primaries.indexing.delete_time_in_millis',
        lambda ms: ms_to_second(ms),
    ),
    'elasticsearch.primaries.indexing.delete.current': ('gauge', '_all.primaries.indexing.delete_current'),
    'elasticsearch.primaries.get.total': ('gauge', '_all.primaries.get.total'),
    'elasticsearch.primaries.get.time': ('gauge', '_all.primaries.get.time_in_millis', lambda ms: ms_to_second(ms)),
    'elasticsearch.primaries.get.current': ('gauge', '_all.primaries.get.current'),
    'elasticsearch.primaries.get.exists.total': ('gauge', '_all.primaries.get.exists_total'),
    'elasticsearch.primaries.get.exists.time': (
        'gauge',
        '_all.primaries.get.exists_time_in_millis',
        lambda ms: ms_to_second(ms),
    ),
    'elasticsearch.primaries.get.missing.total': ('gauge', '_all.primaries.get.missing_total'),
    'elasticsearch.primaries.get.missing.time': (
        'gauge',
        '_all.primaries.get.missing_time_in_millis',
        lambda ms: ms_to_second(ms),
    ),
    'elasticsearch.primaries.search.query.total': ('gauge', '_all.primaries.search.query_total'),
    'elasticsearch.primaries.search.query.time': (
        'gauge',
        '_all.primaries.search.query_time_in_millis',
        lambda ms: ms_to_second(ms),
    ),
    'elasticsearch.primaries.search.query.current': ('gauge', '_all.primaries.search.query_current'),
    'elasticsearch.primaries.search.fetch.total': ('gauge', '_all.primaries.search.fetch_total'),
    'elasticsearch.primaries.search.fetch.time': (
        'gauge',
        '_all.primaries.search.fetch_time_in_millis',
        lambda ms: ms_to_second(ms),
    ),
    'elasticsearch.primaries.search.fetch.current': ('gauge', '_all.primaries.search.fetch_current'),
    'elasticsearch.indices.count': ('gauge', 'indices', lambda indices: len(indices)),
}

PRIMARY_SHARD_METRICS_POST_7_2_0 = {
    'elasticsearch.primaries.refresh.external.total': ('gauge', '_all.primaries.refresh.external_total'),
    'elasticsearch.primaries.refresh.external.total.time': (
        'gauge',
        '_all.primaries.refresh.external_total_time_in_millis',
        lambda ms: ms_to_second(ms),
    ),
}

PRIMARY_SHARD_METRICS_POST_1_0_0 = {
    'elasticsearch.primaries.merges.current': ('gauge', '_all.primaries.merges.current'),
    'elasticsearch.primaries.merges.current.docs': ('gauge', '_all.primaries.merges.current_docs'),
    'elasticsearch.primaries.merges.current.size': ('gauge', '_all.primaries.merges.current_size_in_bytes'),
    'elasticsearch.primaries.merges.total': ('gauge', '_all.primaries.merges.total'),
    'elasticsearch.primaries.merges.total.time': (
        'gauge',
        '_all.primaries.merges.total_time_in_millis',
        lambda ms: ms_to_second(ms),
    ),
    'elasticsearch.primaries.merges.total.docs': ('gauge', '_all.primaries.merges.total_docs'),
    'elasticsearch.primaries.merges.total.size': ('gauge', '_all.primaries.merges.total_size_in_bytes'),
    'elasticsearch.primaries.refresh.total': ('gauge', '_all.primaries.refresh.total'),
    'elasticsearch.primaries.refresh.total.time': (
        'gauge',
        '_all.primaries.refresh.total_time_in_millis',
        lambda ms: ms_to_second(ms),
    ),
    'elasticsearch.primaries.flush.total': ('gauge', '_all.primaries.flush.total'),
    'elasticsearch.primaries.flush.total.time': (
        'gauge',
        '_all.primaries.flush.total_time_in_millis',
        lambda ms: ms_to_second(ms),
    ),
}

# Metrics that are common to all Elasticsearch versions
STATS_METRICS = {
    'elasticsearch.docs.count': ('gauge', 'indices.docs.count'),
    'elasticsearch.docs.deleted': ('gauge', 'indices.docs.deleted'),
    'elasticsearch.store.size': ('gauge', 'indices.store.size_in_bytes'),
    'elasticsearch.indexing.index.total': ('gauge', 'indices.indexing.index_total'),
    'elasticsearch.indexing.index.total.count': ('monotonic_count', 'indices.indexing.index_total'),
    'elasticsearch.indexing.index.time': (
        'gauge',
        'indices.indexing.index_time_in_millis',
        lambda ms: ms_to_second(ms),
    ),
    'elasticsearch.indexing.index.time.count': (
        'monotonic_count',
        'indices.indexing.index_time_in_millis',
        lambda ms: ms_to_second(ms),
    ),
    'elasticsearch.indexing.index.current': ('gauge', 'indices.indexing.index_current'),
    'elasticsearch.indexing.delete.total': ('gauge', 'indices.indexing.delete_total'),
    'elasticsearch.indexing.delete.total.count': ('monotonic_count', 'indices.indexing.delete_total'),
    'elasticsearch.indexing.delete.time': (
        'gauge',
        'indices.indexing.delete_time_in_millis',
        lambda ms: ms_to_second(ms),
    ),
    'elasticsearch.indexing.delete.time.count': (
        'monotonic_count',
        'indices.indexing.delete_time_in_millis',
        lambda ms: ms_to_second(ms),
    ),
    'elasticsearch.indexing.delete.current': ('gauge', 'indices.indexing.delete_current'),
    'elasticsearch.get.total': ('gauge', 'indices.get.total'),
    'elasticsearch.get.total.count': ('monotonic_count', 'indices.get.total'),
    'elasticsearch.get.time': ('gauge', 'indices.get.time_in_millis', lambda ms: ms_to_second(ms)),
    'elasticsearch.get.time.count': ('monotonic_count', 'indices.get.time_in_millis', lambda ms: ms_to_second(ms)),
    'elasticsearch.get.current': ('gauge', 'indices.get.current'),
    'elasticsearch.get.exists.total': ('gauge', 'indices.get.exists_total'),
    'elasticsearch.get.exists.total.count': ('monotonic_count', 'indices.get.exists_total'),
    'elasticsearch.get.exists.time': ('gauge', 'indices.get.exists_time_in_millis', lambda ms: ms_to_second(ms)),
    'elasticsearch.get.exists.time.count': (
        'monotonic_count',
        'indices.get.exists_time_in_millis',
        lambda ms: ms_to_second(ms),
    ),
    'elasticsearch.get.missing.total': ('gauge', 'indices.get.missing_total'),
    'elasticsearch.get.missing.total.count': ('monotonic_count', 'indices.get.missing_total'),
    'elasticsearch.get.missing.time': ('gauge', 'indices.get.missing_time_in_millis', lambda ms: ms_to_second(ms)),
    'elasticsearch.get.missing.time.count': (
        'monotonic_count',
        'indices.get.missing_time_in_millis',
        lambda ms: ms_to_second(ms),
    ),
    'elasticsearch.search.query.total': ('gauge', 'indices.search.query_total'),
    'elasticsearch.search.query.total.count': ('monotonic_count', 'indices.search.query_total'),
    'elasticsearch.search.query.time': ('gauge', 'indices.search.query_time_in_millis', lambda ms: ms_to_second(ms)),
    'elasticsearch.search.query.time.count': (
        'monotonic_count',
        'indices.search.query_time_in_millis',
        lambda ms: ms_to_second(ms),
    ),
    'elasticsearch.search.query.current': ('gauge', 'indices.search.query_current'),
    'elasticsearch.search.fetch.total': ('gauge', 'indices.search.fetch_total'),
    'elasticsearch.search.fetch.total.count': ('monotonic_count', 'indices.search.fetch_total'),
    'elasticsearch.search.fetch.time': ('gauge', 'indices.search.fetch_time_in_millis', lambda ms: ms_to_second(ms)),
    'elasticsearch.search.fetch.time.count': (
        'monotonic_count',
        'indices.search.fetch_time_in_millis',
        lambda ms: ms_to_second(ms),
    ),
    'elasticsearch.search.fetch.current': ('gauge', 'indices.search.fetch_current'),
    'elasticsearch.indices.segments.count': ('gauge', 'indices.segments.count'),
    'elasticsearch.indices.segments.memory_in_bytes': ('gauge', 'indices.segments.memory_in_bytes'),
    'elasticsearch.merges.current': ('gauge', 'indices.merges.current'),
    'elasticsearch.merges.current.docs': ('gauge', 'indices.merges.current_docs'),
    'elasticsearch.merges.current.size': ('gauge', 'indices.merges.current_size_in_bytes'),
    'elasticsearch.merges.total': ('gauge', 'indices.merges.total'),
    'elasticsearch.merges.total.count': ('monotonic_count', 'indices.merges.total'),
    'elasticsearch.merges.total.time': ('gauge', 'indices.merges.total_time_in_millis', lambda ms: ms_to_second(ms)),
    'elasticsearch.merges.total.time.count': (
        'monotonic_count',
        'indices.merges.total_time_in_millis',
        lambda ms: ms_to_second(ms),
    ),
    'elasticsearch.merges.total.docs': ('gauge', 'indices.merges.total_docs'),
    'elasticsearch.merges.total.docs.count': ('monotonic_count', 'indices.merges.total_docs'),
    'elasticsearch.merges.total.size': ('gauge', 'indices.merges.total_size_in_bytes'),
    'elasticsearch.merges.total.size.count': ('monotonic_count', 'indices.merges.total_size_in_bytes'),
    'elasticsearch.refresh.total': ('gauge', 'indices.refresh.total'),
    'elasticsearch.refresh.total.count': ('monotonic_count', 'indices.refresh.total'),
    'elasticsearch.refresh.total.time': ('gauge', 'indices.refresh.total_time_in_millis', lambda ms: ms_to_second(ms)),
    'elasticsearch.refresh.total.time.count': (
        'monotonic_count',
        'indices.refresh.total_time_in_millis',
        lambda ms: ms_to_second(ms),
    ),
    'elasticsearch.flush.total': ('gauge', 'indices.flush.total'),
    'elasticsearch.flush.total.count': ('monotonic_count', 'indices.flush.total'),
    'elasticsearch.flush.total.time': ('gauge', 'indices.flush.total_time_in_millis', lambda ms: ms_to_second(ms)),
    'elasticsearch.flush.total.time.count': (
        'monotonic_count',
        'indices.flush.total_time_in_millis',
        lambda ms: ms_to_second(ms),
    ),
    'elasticsearch.process.open_fd': ('gauge', 'process.open_file_descriptors'),
    'elasticsearch.transport.rx_count': ('gauge', 'transport.rx_count'),
    'elasticsearch.transport.rx_count.count': ('monotonic_count', 'transport.rx_count'),
    'elasticsearch.transport.tx_count': ('gauge', 'transport.tx_count'),
    'elasticsearch.transport.tx_count.count': ('monotonic_count', 'transport.tx_count'),
    'elasticsearch.transport.rx_size': ('gauge', 'transport.rx_size_in_bytes'),
    'elasticsearch.transport.rx_size.count': ('monotonic_count', 'transport.rx_size_in_bytes'),
    'elasticsearch.transport.tx_size': ('gauge', 'transport.tx_size_in_bytes'),
    'elasticsearch.transport.tx_size.count': ('monotonic_count', 'transport.tx_size_in_bytes'),
    'elasticsearch.transport.server_open': ('gauge', 'transport.server_open'),
    'elasticsearch.thread_pool.flush.active': ('gauge', 'thread_pool.flush.active'),
    'elasticsearch.thread_pool.flush.threads': ('gauge', 'thread_pool.flush.threads'),
    'elasticsearch.thread_pool.flush.threads.count': ('monotonic_count', 'thread_pool.flush.threads'),
    'elasticsearch.thread_pool.flush.queue': ('gauge', 'thread_pool.flush.queue'),
    'elasticsearch.thread_pool.flush.rejected': ('rate', 'thread_pool.flush.rejected'),
    'elasticsearch.thread_pool.flush.rejected.count': ('monotonic_count', 'thread_pool.flush.rejected'),
    'elasticsearch.thread_pool.flush.completed': ('gauge', 'thread_pool.flush.completed'),
    'elasticsearch.thread_pool.flush.completed.count': ('monotonic_count', 'thread_pool.flush.completed'),
    'elasticsearch.thread_pool.generic.active': ('gauge', 'thread_pool.generic.active'),
    'elasticsearch.thread_pool.generic.threads': ('gauge', 'thread_pool.generic.threads'),
    'elasticsearch.thread_pool.generic.threads.count': ('monotonic_count', 'thread_pool.generic.threads'),
    'elasticsearch.thread_pool.generic.queue': ('gauge', 'thread_pool.generic.queue'),
    'elasticsearch.thread_pool.generic.rejected': ('rate', 'thread_pool.generic.rejected'),
    'elasticsearch.thread_pool.generic.rejected.count': ('monotonic_count', 'thread_pool.generic.rejected'),
    'elasticsearch.thread_pool.generic.completed': ('gauge', 'thread_pool.generic.completed'),
    'elasticsearch.thread_pool.generic.completed.count': ('monotonic_count', 'thread_pool.generic.completed'),
    'elasticsearch.thread_pool.get.active': ('gauge', 'thread_pool.get.active'),
    'elasticsearch.thread_pool.get.threads': ('gauge', 'thread_pool.get.threads'),
    'elasticsearch.thread_pool.get.threads.count': ('monotonic_count', 'thread_pool.get.threads'),
    'elasticsearch.thread_pool.get.queue': ('gauge', 'thread_pool.get.queue'),
    'elasticsearch.thread_pool.get.rejected': ('rate', 'thread_pool.get.rejected'),
    'elasticsearch.thread_pool.get.rejected.count': ('monotonic_count', 'thread_pool.get.rejected'),
    'elasticsearch.thread_pool.get.completed': ('gauge', 'thread_pool.get.completed'),
    'elasticsearch.thread_pool.get.completed.count': ('monotonic_count', 'thread_pool.get.completed'),
    'elasticsearch.thread_pool.management.active': ('gauge', 'thread_pool.management.active'),
    'elasticsearch.thread_pool.management.threads': ('gauge', 'thread_pool.management.threads'),
    'elasticsearch.thread_pool.management.threads.count': ('monotonic_count', 'thread_pool.management.threads'),
    'elasticsearch.thread_pool.management.queue': ('gauge', 'thread_pool.management.queue'),
    'elasticsearch.thread_pool.management.rejected': ('rate', 'thread_pool.management.rejected'),
    'elasticsearch.thread_pool.management.rejected.count': ('monotonic_count', 'thread_pool.management.rejected'),
    'elasticsearch.thread_pool.management.completed': ('gauge', 'thread_pool.management.completed'),
    'elasticsearch.thread_pool.management.completed.count': ('monotonic_count', 'thread_pool.management.completed'),
    'elasticsearch.thread_pool.refresh.active': ('gauge', 'thread_pool.refresh.active'),
    'elasticsearch.thread_pool.refresh.threads': ('gauge', 'thread_pool.refresh.threads'),
    'elasticsearch.thread_pool.refresh.threads.count': ('monotonic_count', 'thread_pool.refresh.threads'),
    'elasticsearch.thread_pool.refresh.queue': ('gauge', 'thread_pool.refresh.queue'),
    'elasticsearch.thread_pool.refresh.rejected': ('rate', 'thread_pool.refresh.rejected'),
    'elasticsearch.thread_pool.refresh.rejected.count': ('monotonic_count', 'thread_pool.refresh.rejected'),
    'elasticsearch.thread_pool.refresh.completed': ('gauge', 'thread_pool.refresh.completed'),
    'elasticsearch.thread_pool.refresh.completed.count': ('monotonic_count', 'thread_pool.refresh.completed'),
    'elasticsearch.thread_pool.search.active': ('gauge', 'thread_pool.search.active'),
    'elasticsearch.thread_pool.search.threads': ('gauge', 'thread_pool.search.threads'),
    'elasticsearch.thread_pool.search.threads.count': ('monotonic_count', 'thread_pool.search.threads'),
    'elasticsearch.thread_pool.search.queue': ('gauge', 'thread_pool.search.queue'),
    'elasticsearch.thread_pool.search.rejected': ('rate', 'thread_pool.search.rejected'),
    'elasticsearch.thread_pool.search.rejected.count': ('monotonic_count', 'thread_pool.search.rejected'),
    'elasticsearch.thread_pool.search.completed': ('gauge', 'thread_pool.search.completed'),
    'elasticsearch.thread_pool.search.completed.count': ('monotonic_count', 'thread_pool.search.completed'),
    'elasticsearch.thread_pool.snapshot.active': ('gauge', 'thread_pool.snapshot.active'),
    'elasticsearch.thread_pool.snapshot.threads': ('gauge', 'thread_pool.snapshot.threads'),
    'elasticsearch.thread_pool.snapshot.threads.count': ('monotonic_count', 'thread_pool.snapshot.threads'),
    'elasticsearch.thread_pool.snapshot.queue': ('gauge', 'thread_pool.snapshot.queue'),
    'elasticsearch.thread_pool.snapshot.rejected': ('rate', 'thread_pool.snapshot.rejected'),
    'elasticsearch.thread_pool.snapshot.rejected.count': ('monotonic_count', 'thread_pool.snapshot.rejected'),
    'elasticsearch.thread_pool.snapshot.completed': ('gauge', 'thread_pool.snapshot.completed'),
    'elasticsearch.thread_pool.snapshot.completed.count': ('monotonic_count', 'thread_pool.snapshot.completed'),
    'elasticsearch.thread_pool.warmer.active': ('gauge', 'thread_pool.warmer.active'),
    'elasticsearch.thread_pool.warmer.threads': ('gauge', 'thread_pool.warmer.threads'),
    'elasticsearch.thread_pool.warmer.queue': ('gauge', 'thread_pool.warmer.queue'),
    'elasticsearch.thread_pool.warmer.rejected': ('rate', 'thread_pool.warmer.rejected'),
    'elasticsearch.thread_pool.warmer.rejected.count': ('monotonic_count', 'thread_pool.warmer.rejected'),
    'elasticsearch.thread_pool.warmer.completed': ('gauge', 'thread_pool.warmer.completed'),
    'elasticsearch.http.current_open': ('gauge', 'http.current_open'),
    'elasticsearch.http.total_opened': ('gauge', 'http.total_opened'),
    'elasticsearch.http.total_opened.count': ('monotonic_count', 'http.total_opened'),
    'jvm.mem.heap_committed': ('gauge', 'jvm.mem.heap_committed_in_bytes'),
    'jvm.mem.heap_used': ('gauge', 'jvm.mem.heap_used_in_bytes'),
    'jvm.mem.heap_in_use': ('gauge', 'jvm.mem.heap_used_percent'),
    'jvm.mem.heap_max': ('gauge', 'jvm.mem.heap_max_in_bytes'),
    'jvm.mem.non_heap_committed': ('gauge', 'jvm.mem.non_heap_committed_in_bytes'),
    'jvm.mem.non_heap_used': ('gauge', 'jvm.mem.non_heap_used_in_bytes'),
    'jvm.mem.pools.young.used': ('gauge', 'jvm.mem.pools.young.used_in_bytes'),
    'jvm.mem.pools.young.max': ('gauge', 'jvm.mem.pools.young.max_in_bytes'),
    'jvm.mem.pools.old.used': ('gauge', 'jvm.mem.pools.old.used_in_bytes'),
    'jvm.mem.pools.old.max': ('gauge', 'jvm.mem.pools.old.max_in_bytes'),
    'jvm.mem.pools.survivor.used': ('gauge', 'jvm.mem.pools.survivor.used_in_bytes'),
    'jvm.mem.pools.survivor.max': ('gauge', 'jvm.mem.pools.survivor.max_in_bytes'),
    'jvm.threads.count': ('gauge', 'jvm.threads.count'),
    'jvm.threads.peak_count': ('gauge', 'jvm.threads.peak_count'),
    'elasticsearch.fs.total.total_in_bytes': ('gauge', 'fs.total.total_in_bytes'),
    'elasticsearch.fs.total.free_in_bytes': ('gauge', 'fs.total.free_in_bytes'),
    'elasticsearch.fs.total.available_in_bytes': ('gauge', 'fs.total.available_in_bytes'),
}

ADDITIONAL_METRICS_BY_VERSION = {
    (0, 90, 5): {
        'elasticsearch.search.fetch.open_contexts': ('gauge', 'indices.search.open_contexts'),
        'elasticsearch.fielddata.size': ('gauge', 'indices.fielddata.memory_size_in_bytes'),
        'elasticsearch.fielddata.evictions': ('gauge', 'indices.fielddata.evictions'),
        'elasticsearch.fielddata.evictions.count': ('monotonic_count', 'indices.fielddata.evictions'),
    },
    (1, 0, 0): {
        'elasticsearch.indices.translog.size_in_bytes': ('gauge', 'indices.translog.size_in_bytes'),
        'elasticsearch.indices.translog.operations': ('gauge', 'indices.translog.operations'),
    },
    (1, 3, 0): {
        'elasticsearch.indices.segments.index_writer_memory_in_bytes': (
            'gauge',
            'indices.segments.index_writer_memory_in_bytes',
        ),
        'elasticsearch.indices.segments.version_map_memory_in_bytes': (
            'gauge',
            'indices.segments.version_map_memory_in_bytes',
        ),
    },
    (1, 4, 0): {
        'elasticsearch.indices.indexing.throttle_time': (
            'rate',
            'indices.indexing.throttle_time_in_millis',
            lambda ms: ms_to_second(ms),
        ),
        'elasticsearch.indices.indexing.throttle_time.count': (
            'monotonic_count',
            'indices.indexing.throttle_time_in_millis',
            lambda ms: ms_to_second(ms),
        ),
        'elasticsearch.indices.query_cache.memory_size_in_bytes': (
            'gauge',
            'indices.query_cache.memory_size_in_bytes',
        ),
        'elasticsearch.indices.query_cache.hit_count': ('rate', 'indices.query_cache.hit_count'),
        'elasticsearch.indices.query_cache.hit_count.count': ('monotonic_count', 'indices.query_cache.hit_count'),
        'elasticsearch.indices.query_cache.miss_count': ('rate', 'indices.query_cache.miss_count'),
        'elasticsearch.indices.query_cache.miss_count.total': ('monotonic_count', 'indices.query_cache.miss_count'),
        'elasticsearch.indices.query_cache.evictions': ('rate', 'indices.query_cache.evictions'),
        'elasticsearch.indices.query_cache.evictions.count': ('monotonic_count', 'indices.query_cache.evictions'),
        'elasticsearch.indices.segments.index_writer_max_memory_in_bytes': (
            'gauge',
            'indices.segments.index_writer_max_memory_in_bytes',
        ),
        'elasticsearch.indices.segments.fixed_bit_set_memory_in_bytes': (
            'gauge',
            'indices.segments.fixed_bit_set_memory_in_bytes',
        ),
        'elasticsearch.breakers.fielddata.estimated_size_in_bytes': (
            'gauge',
            'breakers.fielddata.estimated_size_in_bytes',
        ),
        'elasticsearch.breakers.fielddata.overhead': ('gauge', 'breakers.fielddata.overhead'),
        'elasticsearch.breakers.fielddata.tripped': ('rate', 'breakers.fielddata.tripped'),
        'elasticsearch.breakers.parent.estimated_size_in_bytes': (
            'gauge',
            'breakers.parent.estimated_size_in_bytes',
        ),
        'elasticsearch.breakers.parent.overhead': ('gauge', 'breakers.parent.overhead'),
        'elasticsearch.breakers.parent.tripped': ('rate', 'breakers.parent.tripped'),
        'elasticsearch.breakers.request.estimated_size_in_bytes': (
            'gauge',
            'breakers.request.estimated_size_in_bytes',
        ),
        'elasticsearch.breakers.request.overhead': ('gauge', 'breakers.request.overhead'),
        'elasticsearch.breakers.request.tripped': ('rate', 'breakers.request.tripped'),
    },
    (1, 5, 0): {
        'elasticsearch.indices.recovery.current_as_source': ('gauge', 'indices.recovery.current_as_source'),
        'elasticsearch.indices.recovery.current_as_target': ('gauge', 'indices.recovery.current_as_target'),
        'elasticsearch.indices.recovery.throttle_time': (
            'rate',
            'indices.recovery.throttle_time_in_millis',
            lambda ms: ms_to_second(ms),
        ),
        'elasticsearch.indices.recovery.throttle_time.count': (
            'monotonic_count',
            'indices.recovery.throttle_time_in_millis',
            lambda ms: ms_to_second(ms),
        ),
    },
    (1, 6, 0): {
        'elasticsearch.thread_pool.fetch_shard_started.active': ('gauge', 'thread_pool.fetch_shard_started.active'),
        'elasticsearch.thread_pool.fetch_shard_started.threads': (
            'gauge',
            'thread_pool.fetch_shard_started.threads',
        ),
        'elasticsearch.thread_pool.fetch_shard_started.queue': ('gauge', 'thread_pool.fetch_shard_started.queue'),
        'elasticsearch.thread_pool.fetch_shard_started.rejected': (
            'rate',
            'thread_pool.fetch_shard_started.rejected',
        ),
        'elasticsearch.thread_pool.fetch_shard_store.active': ('gauge', 'thread_pool.fetch_shard_store.active'),
        'elasticsearch.thread_pool.fetch_shard_store.threads': ('gauge', 'thread_pool.fetch_shard_store.threads'),
        'elasticsearch.thread_pool.fetch_shard_store.queue': ('gauge', 'thread_pool.fetch_shard_store.queue'),
        'elasticsearch.thread_pool.fetch_shard_store.rejected': ('rate', 'thread_pool.fetch_shard_store.rejected'),
    },
    (2, 0, 0): {
        # Some of these may very well exist in previous ES versions, but not worth the time/effort
        # to find where they were introduced
        'elasticsearch.indices.query_cache.cache_size': ('gauge', 'indices.query_cache.cache_size'),
        'elasticsearch.indices.query_cache.cache_count': ('monotonic_count', 'indices.query_cache.cache_count'),
        'elasticsearch.indices.query_cache.total_count': ('monotonic_count', 'indices.query_cache.total_count'),
        'elasticsearch.indices.segments.doc_values_memory_in_bytes': (
            'gauge',
            'indices.segments.doc_values_memory_in_bytes',
        ),
        'elasticsearch.indices.segments.norms_memory_in_bytes': ('gauge', 'indices.segments.norms_memory_in_bytes'),
        'elasticsearch.indices.segments.stored_fields_memory_in_bytes': (
            'gauge',
            'indices.segments.stored_fields_memory_in_bytes',
        ),
        'elasticsearch.indices.segments.term_vectors_memory_in_bytes': (
            'gauge',
            'indices.segments.term_vectors_memory_in_bytes',
        ),
        'elasticsearch.indices.segments.terms_memory_in_bytes': ('gauge', 'indices.segments.terms_memory_in_bytes'),
        'elasticsearch.indices.request_cache.memory_size_in_bytes': (
            'gauge',
            'indices.request_cache.memory_size_in_bytes',
        ),
        'elasticsearch.indices.request_cache.evictions': ('rate', 'indices.request_cache.evictions'),
        'elasticsearch.indices.request_cache.evictions.count': (
            'monotonic_count',
            'indices.request_cache.evictions',
        ),
        'elasticsearch.indices.request_cache.hit_count': ('rate', 'indices.request_cache.hit_count'),
        'elasticsearch.indices.request_cache.hit_count.count': (
            'monotonic_count',
            'indices.request_cache.hit_count',
        ),
        'elasticsearch.indices.request_cache.miss_count': ('rate', 'indices.request_cache.miss_count'),
        'elasticsearch.indices.request_cache.miss_count.count': (
            'monotonic_count',
            'indices.request_cache.miss_count',
        ),
    },
    (2, 1, 0): {
        'elasticsearch.indices.indexing.index_failed.count': ('monotonic_count', 'indices.indexing.index_failed'),
        'elasticsearch.indices.indexing.index_failed': ('rate', 'indices.indexing.index_failed'),
        'elasticsearch.thread_pool.force_merge.active': ('gauge', 'thread_pool.force_merge.active'),
        'elasticsearch.thread_pool.force_merge.threads': ('gauge', 'thread_pool.force_merge.threads'),
        'elasticsearch.thread_pool.force_merge.queue': ('gauge', 'thread_pool.force_merge.queue'),
        'elasticsearch.thread_pool.force_merge.rejected': ('rate', 'thread_pool.force_merge.rejected'),
        'elasticsearch.thread_pool.force_merge.rejected.count': (
            'monotonic_count',
            'thread_pool.force_merge.rejected',
        ),
    },
    (5, 0, 0): {
        'elasticsearch.fs.total.disk_io_op': ('rate', 'fs.io_stats.total.operations'),
        'elasticsearch.fs.total.disk_reads': ('rate', 'fs.io_stats.total.read_operations'),
        'elasticsearch.fs.total.disk_writes': ('rate', 'fs.io_stats.total.write_operations'),
        'elasticsearch.fs.total.disk_read_size_in_bytes': ('gauge', 'fs.io_stats.total.read_kilobytes'),
        'elasticsearch.fs.total.disk_write_size_in_bytes': ('gauge', 'fs.io_stats.total.write_kilobytes'),
        'elasticsearch.search.scroll.total': ('gauge', 'indices.search.scroll_total'),
        'elasticsearch.search.scroll.total.count': ('monotonic_count', 'indices.search.scroll_total'),
        'elasticsearch.search.scroll.time': (
            'gauge',
            'indices.search.scroll_time_in_millis',
            lambda ms: ms_to_second(ms),
        ),
        'elasticsearch.search.scroll.time.count': (
            'monotonic_count',
            'indices.search.scroll_time_in_millis',
            lambda ms: ms_to_second(ms),
        ),
        'elasticsearch.search.scroll.current': ('gauge', 'indices.search.scroll_current'),
    },
    (6, 3, 0): {
        'elasticsearch.thread_pool.write.active': ('gauge', 'thread_pool.write.active'),
        'elasticsearch.thread_pool.write.threads': ('gauge', 'thread_pool.write.threads'),
        'elasticsearch.thread_pool.write.threads.count': ('monotonic_count', 'thread_pool.write.threads'),
        'elasticsearch.thread_pool.write.queue': ('gauge', 'thread_pool.write.queue'),
        'elasticsearch.thread_pool.write.rejected': ('rate', 'thread_pool.write.rejected'),
        'elasticsearch.thread_pool.write.rejected.count': ('monotonic_count', 'thread_pool.write.rejected'),
        'elasticsearch.thread_pool.write.completed': ('rate', 'thread_pool.write.completed'),
        'elasticsearch.thread_pool.write.completed.count': ('monotonic_count', 'thread_pool.write.completed'),
    },
    (7, 2, 0): {
        'elasticsearch.refresh.external.total': ('gauge', 'indices.refresh.external_total'),
        'elasticsearch.refresh.external.total.time': (
            'gauge',
            'indices.refresh.external_total_time_in_millis',
            lambda ms: ms_to_second(ms),
        ),
    },
    (7, 9, 0): {
        'elasticsearch.indexing_pressure.memory.current.coordinating_in_bytes': (
            'gauge',
            'indexing_pressure.memory.current.coordinating_in_bytes',
        ),
        'elasticsearch.indexing_pressure.memory.current.primary_in_bytes': (
            'gauge',
            'indexing_pressure.memory.current.primary_in_bytes',
        ),
        'elasticsearch.indexing_pressure.memory.current.replica_in_bytes': (
            'gauge',
            'indexing_pressure.memory.current.replica_in_bytes',
        ),
        'elasticsearch.indexing_pressure.memory.current.all_in_bytes': (
            'gauge',
            'indexing_pressure.memory.current.all_in_bytes',
        ),
        'elasticsearch.indexing_pressure.memory.current.combined_coordinating_and_primary_in_bytes': (
            'gauge',
            'indexing_pressure.memory.current.combined_coordinating_and_primary_in_bytes',
        ),
        'elasticsearch.indexing_pressure.memory.total.coordinating_in_bytes': (
            'gauge',
            'indexing_pressure.memory.total.coordinating_in_bytes',
        ),
        'elasticsearch.indexing_pressure.memory.total.primary_in_bytes': (
            'gauge',
            'indexing_pressure.memory.total.primary_in_bytes',
        ),
        'elasticsearch.indexing_pressure.memory.total.replica_in_bytes': (
            'gauge',
            'indexing_pressure.memory.total.replica_in_bytes',
        ),
        'elasticsearch.indexing_pressure.memory.total.all_in_bytes': (
            'gauge',
            'indexing_pressure.memory.total.all_in_bytes',
        ),
        'elasticsearch.indexing_pressure.memory.total.combined_coordinating_and_primary_in_bytes': (
            'gauge',
            'indexing_pressure.memory.total.combined_coordinating_and_primary_in_bytes',
        ),
        'elasticsearch.indexing_pressure.memory.total.coordinating_rejections': (
            'gauge',
            'indexing_pressure.memory.total.coordinating_rejections',
        ),
        'elasticsearch.indexing_pressure.memory.total.primary_rejections': (
            'gauge',
            'indexing_pressure.memory.total.primary_rejections',
        ),
        'elasticsearch.indexing_pressure.memory.total.replica_rejections': (
            'gauge',
            'indexing_pressure.memory.total.replica_rejections',
        ),
    },
    (7, 10, 0): {
        "elasticsearch.indexing_pressure.memory.limit_in_bytes": (
            "gauge",
            "indexing_pressure.memory.limit_in_bytes",
        ),
    },
    (8, 0, 0): {
        # The in_flight_requests stat has been renamed inflight_requests in logs and diagnostic APIs.
        # https://www.elastic.co/guide/en/elasticsearch/reference/current/migrating-8.0.html#breaking_80_rest_api_changes
        'elasticsearch.breakers.inflight_requests.tripped': ('gauge', 'breakers.inflight_requests.tripped'),
        'elasticsearch.breakers.inflight_requests.overhead': ('gauge', 'breakers.inflight_requests.overhead'),
        'elasticsearch.breakers.inflight_requests.estimated_size_in_bytes': (
            'gauge',
            'breakers.inflight_requests.estimated_size_in_bytes',
        ),
    },
}
VERSIONS_THAT_ADD_METRICS = sorted(ADDITIONAL_METRICS_BY_VERSION)

# These metrics have been deleted on ES8
# https://www.elastic.co/guide/en/elasticsearch/reference/current/migrating-8.0.html
ADDITIONAL_METRIC_PRE_8_0_0 = {
    'elasticsearch.thread_pool.listener.active': ('gauge', 'thread_pool.listener.active'),
    'elasticsearch.thread_pool.listener.threads': ('gauge', 'thread_pool.listener.threads'),
    'elasticsearch.thread_pool.listener.threads.count': ('monotonic_count', 'thread_pool.listener.threads'),
    'elasticsearch.thread_pool.listener.queue': ('gauge', 'thread_pool.listener.queue'),
    'elasticsearch.thread_pool.listener.rejected': ('rate', 'thread_pool.listener.rejected'),
    'elasticsearch.thread_pool.listener.rejected.count': ('monotonic_count', 'thread_pool.listener.rejected'),
    'elasticsearch.breakers.inflight_requests.tripped': ('gauge', 'breakers.in_flight_requests.tripped'),
    'elasticsearch.breakers.inflight_requests.overhead': ('gauge', 'breakers.in_flight_requests.overhead'),
    'elasticsearch.breakers.inflight_requests.estimated_size_in_bytes': (
        'gauge',
        'breakers.in_flight_requests.estimated_size_in_bytes',
    ),
}

ADDITIONAL_METRICS_PRE_7_0_0 = {
    'elasticsearch.thread_pool.index.active': ('gauge', 'thread_pool.index.active'),
    'elasticsearch.thread_pool.index.queue': ('gauge', 'thread_pool.index.queue'),
    'elasticsearch.thread_pool.index.threads': ('gauge', 'thread_pool.index.threads'),
    'elasticsearch.thread_pool.index.threads.count': ('monotonic_count', 'thread_pool.index.threads'),
    'elasticsearch.thread_pool.index.rejected': ('rate', 'thread_pool.index.rejected'),
    'elasticsearch.thread_pool.index.rejected.count': ('monotonic_count', 'thread_pool.index.rejected'),
    'elasticsearch.thread_pool.index.completed': ('gauge', 'thread_pool.index.completed'),
    'elasticsearch.thread_pool.index.completed.count': ('monotonic_count', 'thread_pool.index.completed'),
}

ADDITIONAL_METRICS_PRE_5_0_0 = {
    'elasticsearch.thread_pool.percolate.active': ('gauge', 'thread_pool.percolate.active'),
    'elasticsearch.thread_pool.percolate.threads': ('gauge', 'thread_pool.percolate.threads'),
    'elasticsearch.thread_pool.percolate.queue': ('gauge', 'thread_pool.percolate.queue'),
    'elasticsearch.thread_pool.percolate.rejected': ('rate', 'thread_pool.percolate.rejected'),
    'elasticsearch.thread_pool.percolate.rejected.count': ('monotonic_count', 'thread_pool.percolate.rejected'),
    'elasticsearch.thread_pool.suggest.active': ('gauge', 'thread_pool.suggest.active'),
    'elasticsearch.thread_pool.suggest.threads': ('gauge', 'thread_pool.suggest.threads'),
    'elasticsearch.thread_pool.suggest.queue': ('gauge', 'thread_pool.suggest.queue'),
    'elasticsearch.thread_pool.suggest.rejected': ('rate', 'thread_pool.suggest.rejected'),
    'elasticsearch.thread_pool.suggest.rejected.count': ('monotonic_count', 'thread_pool.suggest.rejected'),
}

# Metrics for index level
INDEX_STATS_METRICS = {
    'elasticsearch.index.health': ('gauge', 'health'),
    'elasticsearch.index.health.reverse': ('gauge', 'health_reverse'),
    'elasticsearch.index.docs.count': ('gauge', 'docs_count'),
    'elasticsearch.index.docs.deleted': ('gauge', 'docs_deleted'),
    'elasticsearch.index.primary_shards': ('gauge', 'primary_shards'),
    'elasticsearch.index.replica_shards': ('gauge', 'replica_shards'),
    'elasticsearch.index.primary_store_size': ('gauge', 'primary_store_size'),
    'elasticsearch.index.store_size': ('gauge', 'store_size'),
}
INDEX_SEARCH_STATS = [
    ('elasticsearch.index.search.query.total', 'total.search.query_total'),
    ('elasticsearch.index.search.query.time', 'total.search.query_time_in_millis'),
]


JVM_METRICS_POST_0_90_10 = {
    'jvm.gc.collectors.young.count': ('gauge', 'jvm.gc.collectors.young.collection_count'),
    'jvm.gc.collectors.young.collection_time': (
        'gauge',
        'jvm.gc.collectors.young.collection_time_in_millis',
        lambda ms: ms_to_second(ms),
    ),
    'jvm.gc.collectors.old.count': ('gauge', 'jvm.gc.collectors.old.collection_count'),
    'jvm.gc.collectors.old.collection_time': (
        'gauge',
        'jvm.gc.collectors.old.collection_time_in_millis',
        lambda ms: ms_to_second(ms),
    ),
}

JVM_METRICS_RATE = {
    # Submit metrics as rate
    'jvm.gc.collectors.young.rate': ('rate', 'jvm.gc.collectors.young.collection_count'),
    'jvm.gc.collectors.young.collection_time.rate': (
        'rate',
        'jvm.gc.collectors.young.collection_time_in_millis',
        lambda ms: ms_to_second(ms),
    ),
    'jvm.gc.collectors.old.rate': ('rate', 'jvm.gc.collectors.old.collection_count'),
    'jvm.gc.collectors.old.collection_time.rate': (
        'rate',
        'jvm.gc.collectors.old.collection_time_in_millis',
        lambda ms: ms_to_second(ms),
    ),
}

JVM_METRICS_PRE_0_90_10 = {
    'jvm.gc.concurrent_mark_sweep.count': ('gauge', 'jvm.gc.collectors.ConcurrentMarkSweep.collection_count'),
    'jvm.gc.concurrent_mark_sweep.collection_time': (
        'gauge',
        'jvm.gc.collectors.ConcurrentMarkSweep.collection_time_in_millis',
        lambda ms: ms_to_second(ms),
    ),
    'jvm.gc.par_new.count': ('gauge', 'jvm.gc.collectors.ParNew.collection_count'),
    'jvm.gc.par_new.collection_time': (
        'gauge',
        'jvm.gc.collectors.ParNew.collection_time_in_millis',
        lambda ms: ms_to_second(ms),
    ),
    'jvm.gc.collection_count': ('gauge', 'jvm.gc.collection_count'),
    'jvm.gc.collection_time': ('gauge', 'jvm.gc.collection_time_in_millis', lambda ms: ms_to_second(ms)),
}


ADDITIONAL_METRICS_POST_0_90_5_PRE_2_0 = {
    'elasticsearch.cache.filter.evictions': ('gauge', 'indices.filter_cache.evictions'),
    'elasticsearch.cache.filter.evictions.count': ('monotonic_count', 'indices.filter_cache.evictions'),
    'elasticsearch.cache.filter.size': ('gauge', 'indices.filter_cache.memory_size_in_bytes'),
    'elasticsearch.id_cache.size': ('gauge', 'indices.id_cache.memory_size_in_bytes'),
}

ADDITIONAL_METRICS_PRE_0_90_5 = {
    'elasticsearch.cache.field.evictions': ('gauge', 'indices.cache.field_evictions'),
    'elasticsearch.cache.field.size': ('gauge', 'indices.cache.field_size_in_bytes'),
    'elasticsearch.cache.filter.count': ('gauge', 'indices.cache.filter_count'),
    'elasticsearch.cache.filter.evictions': ('gauge', 'indices.cache.filter_evictions'),
    'elasticsearch.cache.filter.size': ('gauge', 'indices.cache.filter_size_in_bytes'),
}

# Stats are only valid for v1.x
ADDITIONAL_METRICS_1_x = {
    'elasticsearch.fs.total.disk_reads': ('rate', 'fs.total.disk_reads'),
    'elasticsearch.fs.total.disk_writes': ('rate', 'fs.total.disk_writes'),
    'elasticsearch.fs.total.disk_io_op': ('rate', 'fs.total.disk_io_op'),
    'elasticsearch.fs.total.disk_read_size_in_bytes': ('gauge', 'fs.total.disk_read_size_in_bytes'),
    'elasticsearch.fs.total.disk_write_size_in_bytes': ('gauge', 'fs.total.disk_write_size_in_bytes'),
    'elasticsearch.fs.total.disk_io_size_in_bytes': ('gauge', 'fs.total.disk_io_size_in_bytes'),
}


ADDITIONAL_METRICS_PRE_2_0 = {
    'elasticsearch.thread_pool.merge.active': ('gauge', 'thread_pool.merge.active'),
    'elasticsearch.thread_pool.merge.threads': ('gauge', 'thread_pool.merge.threads'),
    'elasticsearch.thread_pool.merge.queue': ('gauge', 'thread_pool.merge.queue'),
    'elasticsearch.thread_pool.merge.rejected': ('rate', 'thread_pool.merge.rejected'),
}


ADDITIONAL_METRICS_PRE_6_3 = {
    'elasticsearch.thread_pool.bulk.active': ('gauge', 'thread_pool.bulk.active'),
    'elasticsearch.thread_pool.bulk.threads': ('gauge', 'thread_pool.bulk.threads'),
    'elasticsearch.thread_pool.bulk.threads.count': ('monotonic_count', 'thread_pool.bulk.threads'),
    'elasticsearch.thread_pool.bulk.queue': ('gauge', 'thread_pool.bulk.queue'),
    'elasticsearch.thread_pool.bulk.rejected': ('rate', 'thread_pool.bulk.rejected'),
    'elasticsearch.thread_pool.bulk.rejected.count': ('monotonic_count', 'thread_pool.bulk.rejected'),
    'elasticsearch.thread_pool.bulk.completed': ('rate', 'thread_pool.bulk.completed'),
    'elasticsearch.thread_pool.bulk.completed.count': ('monotonic_count', 'thread_pool.bulk.completed'),
}


CLUSTER_HEALTH_METRICS = {
    'elasticsearch.number_of_nodes': ('gauge', 'number_of_nodes'),
    'elasticsearch.number_of_data_nodes': ('gauge', 'number_of_data_nodes'),
    'elasticsearch.active_primary_shards': ('gauge', 'active_primary_shards'),
    'elasticsearch.active_shards': ('gauge', 'active_shards'),
    'elasticsearch.relocating_shards': ('gauge', 'relocating_shards'),
    'elasticsearch.initializing_shards': ('gauge', 'initializing_shards'),
    'elasticsearch.unassigned_shards': ('gauge', 'unassigned_shards'),
    'elasticsearch.cluster_status': ('gauge', 'status', lambda v: {'red': 0, 'yellow': 1, 'green': 2}.get(v, -1)),
}

CLUSTER_HEALTH_METRICS_POST_2_4 = {'elasticsearch.delayed_unassigned_shards': ('gauge', 'delayed_unassigned_shards')}

CLUSTER_PENDING_TASKS = {
    'elasticsearch.pending_tasks_total': ('gauge', 'pending_task_total'),
    'elasticsearch.pending_tasks_priority_high': ('gauge', 'pending_tasks_priority_high'),
    'elasticsearch.pending_tasks_priority_urgent': ('gauge', 'pending_tasks_priority_urgent'),
    'elasticsearch.pending_tasks_time_in_queue': ('gauge', 'pending_tasks_time_in_queue'),
}

SLM_POLICY_METRICS = {
    'elasticsearch.slm.snapshot_deletion_failures': ('gauge', 'stats.snapshot_deletion_failures'),
    'elasticsearch.slm.snapshots_deleted': ('gauge', 'stats.snapshots_deleted'),
    'elasticsearch.slm.snapshots_failed': ('gauge', 'stats.snapshots_failed'),
    'elasticsearch.slm.snapshots_taken': ('gauge', 'stats.snapshots_taken'),
}

NODE_SYSTEM_METRICS = {
    'system.mem.free': ('gauge', 'os.mem.free_in_bytes', lambda b: byte_to_mebibyte(b)),
    'system.mem.usable': ('gauge', 'os.mem.free_in_bytes', lambda b: byte_to_mebibyte(b)),
    'system.mem.used': ('gauge', 'os.mem.used_in_bytes', lambda b: byte_to_mebibyte(b)),
    'system.swap.free': ('gauge', 'os.swap.free_in_bytes', lambda b: byte_to_mebibyte(b)),
    'system.swap.used': ('gauge', 'os.swap.used_in_bytes', lambda b: byte_to_mebibyte(b)),
    'system.net.bytes_rcvd': ('gauge', 'transport.rx_size_in_bytes'),
    'system.net.bytes_sent': ('gauge', 'transport.tx_size_in_bytes'),
}

NODE_SYSTEM_METRICS_POST_1 = {
    'system.mem.total': ('gauge', 'os.mem.total_in_bytes', lambda b: byte_to_mebibyte(b)),
    'system.swap.total': ('gauge', 'os.swap.total_in_bytes', lambda b: byte_to_mebibyte(b)),
}

NODE_SYSTEM_METRICS_POST_5 = {
    'system.cpu.idle': ('gauge', 'os.cpu.percent', lambda v: (100 - v)),
    'system.load.1': ('gauge', 'os.cpu.load_average.1m'),
    'system.load.5': ('gauge', 'os.cpu.load_average.5m'),
    'system.load.15': ('gauge', 'os.cpu.load_average.15m'),
    'elasticsearch.cgroup.cpu.stat.number_of_elapsed_periods': (
        'gauge',
        'os.cgroup.cpu.stat.number_of_elapsed_periods',
    ),
    'elasticsearch.cgroup.cpu.stat.number_of_times_throttled': (
        'gauge',
        'os.cgroup.cpu.stat.number_of_times_throttled',
    ),
    'elasticsearch.process.cpu.percent': ('gauge', 'process.cpu.percent'),
}

CAT_ALLOCATION_METRICS = {
    'elasticsearch.shards': ('gauge', 'shards'),
    'elasticsearch.disk.indices': ('gauge', 'disk_indices'),
    'elasticsearch.disk.used': ('gauge', 'disk_used'),
    'elasticsearch.disk.avail': ('gauge', 'disk_avail'),
    'elasticsearch.disk.total': ('gauge', 'disk_total'),
    'elasticsearch.disk.percent': ('gauge', 'disk_percent'),
}

TEMPLATE_METRICS = {
    'elasticsearch.templates.count': ('gauge', 'templates', lambda templates: len(templates)),
}


def stats_for_version(version, jvm_rate=False):
    """
    Get the proper set of stats metrics for the specified ES version
    """
    metrics = dict(STATS_METRICS)

    # JVM additional metrics
    if version >= [0, 90, 10]:
        metrics.update(JVM_METRICS_POST_0_90_10)
        if jvm_rate:
            metrics.update(JVM_METRICS_RATE)
    else:
        metrics.update(JVM_METRICS_PRE_0_90_10)

    # Additional Stats metrics
    if version < [0, 90, 5]:
        metrics.update(ADDITIONAL_METRICS_PRE_0_90_5)

    if version < [2, 0, 0]:
        metrics.update(ADDITIONAL_METRICS_PRE_2_0)
        if version >= [0, 90, 5]:
            metrics.update(ADDITIONAL_METRICS_POST_0_90_5_PRE_2_0)
        if version >= [1, 0, 0]:
            metrics.update(ADDITIONAL_METRICS_1_x)

    if version < [5, 0, 0]:
        metrics.update(ADDITIONAL_METRICS_PRE_5_0_0)
    if version < [6, 3, 0]:
        metrics.update(ADDITIONAL_METRICS_PRE_6_3)
    if version < [7, 0, 0]:
        metrics.update(ADDITIONAL_METRICS_PRE_7_0_0)
    if version < [8, 0, 0]:
        metrics.update(ADDITIONAL_METRIC_PRE_8_0_0)

    for ver in VERSIONS_THAT_ADD_METRICS[: bisect(VERSIONS_THAT_ADD_METRICS, tuple(version))]:
        metrics.update(ADDITIONAL_METRICS_BY_VERSION[ver])

    return metrics


def pshard_stats_for_version(version):
    """
    Get the proper set of pshard metrics for the specified ES version
    """
    pshard_stats_metrics = dict(PRIMARY_SHARD_METRICS)
    if version >= [1, 0, 0]:
        pshard_stats_metrics.update(PRIMARY_SHARD_METRICS_POST_1_0_0)

    if version >= [7, 2, 0]:
        pshard_stats_metrics.update(PRIMARY_SHARD_METRICS_POST_7_2_0)

    return pshard_stats_metrics


def health_stats_for_version(version):
    """
    Get the proper set of health metrics for the specified ES version
    """
    cluster_health_metrics = dict(CLUSTER_HEALTH_METRICS)
    if version >= [2, 4, 0]:
        cluster_health_metrics.update(CLUSTER_HEALTH_METRICS_POST_2_4)

    return cluster_health_metrics


def slm_stats_for_version(version):
    """
    Get the proper set of SLM metrics for the specified ES version
    """
    slm_health_metrics = {}
    if version >= [7, 4, 0]:
        slm_health_metrics.update(dict(SLM_POLICY_METRICS))

    return slm_health_metrics


def index_stats_for_version(version):
    """
    Get the proper set of index metrics for the specified ES version
    """
    index_stats = {}

    if version:
        index_stats.update(INDEX_STATS_METRICS)

    return index_stats


def node_system_stats_for_version(version):
    """
    Get the proper set of os metrics for the specified ES version
    """
    node_system_stats = dict(NODE_SYSTEM_METRICS)

    if version >= [1, 0, 0]:
        node_system_stats.update(NODE_SYSTEM_METRICS_POST_1)
    if version >= [5, 0, 0]:
        node_system_stats.update(NODE_SYSTEM_METRICS_POST_5)

    return node_system_stats
