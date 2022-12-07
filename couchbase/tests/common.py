# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.base.utils.common import get_docker_hostname

HERE = os.path.dirname(os.path.abspath(__file__))

# Networking
HOST = get_docker_hostname()
PORT = '8091'
QUERY_PORT = '8093'
SG_PORT = '4985'
INDEX_STATS_PORT = '9102'

# Tags and common bucket name
CUSTOM_TAGS = ['optional:tag1']
CHECK_TAGS = CUSTOM_TAGS + ['instance:http://{}:{}'.format(HOST, PORT)]
BUCKET_NAME = 'cb_bucket'
INDEX_STATS_TAGS = CHECK_TAGS + [
    'bucket:cb_bucket',
    'collection:default',
    'index_name:gamesim_primary',
    'scope:default',
]

URL = 'http://{}:{}'.format(HOST, PORT)
QUERY_URL = 'http://{}:{}'.format(HOST, QUERY_PORT)
SG_URL = 'http://{}:{}'.format(HOST, SG_PORT)
INDEX_STATS_URL = 'http://{}:{}'.format(HOST, INDEX_STATS_PORT)
CB_CONTAINER_NAME = 'couchbase-standalone'
USER = 'Administrator'
PASSWORD = 'password'

COUCHBASE_MAJOR_VERSION = int(os.getenv('COUCHBASE_VERSION').split(".")[0])

DEFAULT_INSTANCE = {'server': URL, 'user': USER, 'password': PASSWORD, 'timeout': 1, 'tags': CUSTOM_TAGS}

SYNC_GATEWAY_METRICS = [
    "couchbase.sync_gateway.admin_net_bytes_recv",
    "couchbase.sync_gateway.admin_net_bytes_sent",
    "couchbase.sync_gateway.cache.abandoned_seqs",
    "couchbase.sync_gateway.cache.chan_cache_active_revs",
    "couchbase.sync_gateway.cache.chan_cache_bypass_count",
    "couchbase.sync_gateway.cache.chan_cache_channels_added",
    "couchbase.sync_gateway.cache.chan_cache_channels_evicted_inactive",
    "couchbase.sync_gateway.cache.chan_cache_channels_evicted_nru",
    "couchbase.sync_gateway.cache.chan_cache_compact_count",
    "couchbase.sync_gateway.cache.chan_cache_compact_time",
    "couchbase.sync_gateway.cache.chan_cache_hits",
    "couchbase.sync_gateway.cache.chan_cache_max_entries",
    "couchbase.sync_gateway.cache.chan_cache_misses",
    "couchbase.sync_gateway.cache.chan_cache_num_channels",
    "couchbase.sync_gateway.cache.chan_cache_pending_queries",
    "couchbase.sync_gateway.cache.chan_cache_removal_revs",
    "couchbase.sync_gateway.cache.chan_cache_tombstone_revs",
    "couchbase.sync_gateway.cache.high_seq_cached",
    "couchbase.sync_gateway.cache.high_seq_stable",
    "couchbase.sync_gateway.cache.num_active_channels",
    "couchbase.sync_gateway.cache.num_skipped_seqs",
    "couchbase.sync_gateway.cache.pending_seq_len",
    "couchbase.sync_gateway.cache.rev_cache_bypass",
    "couchbase.sync_gateway.cache.rev_cache_hits",
    "couchbase.sync_gateway.cache.rev_cache_misses",
    "couchbase.sync_gateway.cache.skipped_seq_len",
    "couchbase.sync_gateway.cbl_replication_pull.attachment_pull_bytes",
    "couchbase.sync_gateway.cbl_replication_pull.attachment_pull_count",
    "couchbase.sync_gateway.cbl_replication_pull.max_pending",
    "couchbase.sync_gateway.cbl_replication_pull.num_pull_repl_active_continuous",
    "couchbase.sync_gateway.cbl_replication_pull.num_pull_repl_active_one_shot",
    "couchbase.sync_gateway.cbl_replication_pull.num_pull_repl_caught_up",
    "couchbase.sync_gateway.cbl_replication_pull.num_pull_repl_since_zero",
    "couchbase.sync_gateway.cbl_replication_pull.num_pull_repl_total_continuous",
    "couchbase.sync_gateway.cbl_replication_pull.num_pull_repl_total_one_shot",
    "couchbase.sync_gateway.cbl_replication_pull.num_replications_active",
    "couchbase.sync_gateway.cbl_replication_pull.request_changes_count",
    "couchbase.sync_gateway.cbl_replication_pull.request_changes_time",
    "couchbase.sync_gateway.cbl_replication_pull.rev_processing_time",
    "couchbase.sync_gateway.cbl_replication_pull.rev_send_count",
    "couchbase.sync_gateway.cbl_replication_pull.rev_send_latency",
    "couchbase.sync_gateway.cbl_replication_push.attachment_push_bytes",
    "couchbase.sync_gateway.cbl_replication_push.attachment_push_count",
    "couchbase.sync_gateway.cbl_replication_push.doc_push_count",
    "couchbase.sync_gateway.cbl_replication_push.propose_change_count",
    "couchbase.sync_gateway.cbl_replication_push.propose_change_time",
    "couchbase.sync_gateway.cbl_replication_push.sync_function_count",
    "couchbase.sync_gateway.cbl_replication_push.sync_function_time",
    "couchbase.sync_gateway.cbl_replication_push.write_processing_time",
    "couchbase.sync_gateway.database.abandoned_seqs",
    "couchbase.sync_gateway.database.conflict_write_count",
    "couchbase.sync_gateway.database.crc32c_match_count",
    "couchbase.sync_gateway.database.dcp_caching_count",
    "couchbase.sync_gateway.database.dcp_caching_time",
    "couchbase.sync_gateway.database.dcp_received_count",
    "couchbase.sync_gateway.database.dcp_received_time",
    "couchbase.sync_gateway.database.doc_reads_bytes_blip",
    "couchbase.sync_gateway.database.doc_writes_bytes",
    "couchbase.sync_gateway.database.doc_writes_bytes_blip",
    "couchbase.sync_gateway.database.doc_writes_xattr_bytes",
    "couchbase.sync_gateway.database.high_seq_feed",
    "couchbase.sync_gateway.database.num_doc_reads_blip",
    "couchbase.sync_gateway.database.num_doc_reads_rest",
    "couchbase.sync_gateway.database.num_doc_writes",
    "couchbase.sync_gateway.database.num_replications_active",
    "couchbase.sync_gateway.database.num_replications_total",
    "couchbase.sync_gateway.database.num_tombstones_compacted",
    "couchbase.sync_gateway.database.sequence_assigned_count",
    "couchbase.sync_gateway.database.sequence_get_count",
    "couchbase.sync_gateway.database.sequence_incr_count",
    "couchbase.sync_gateway.database.sequence_released_count",
    "couchbase.sync_gateway.database.sequence_reserved_count",
    "couchbase.sync_gateway.database.warn_channels_per_doc_count",
    "couchbase.sync_gateway.database.warn_grants_per_doc_count",
    "couchbase.sync_gateway.database.warn_xattr_size_count",
    "couchbase.sync_gateway.error_count",
    "couchbase.sync_gateway.go_memstats_heapalloc",
    "couchbase.sync_gateway.go_memstats_heapidle",
    "couchbase.sync_gateway.go_memstats_heapinuse",
    "couchbase.sync_gateway.go_memstats_heapreleased",
    "couchbase.sync_gateway.go_memstats_pausetotalns",
    "couchbase.sync_gateway.go_memstats_stackinuse",
    "couchbase.sync_gateway.go_memstats_stacksys",
    "couchbase.sync_gateway.go_memstats_sys",
    "couchbase.sync_gateway.goroutines_high_watermark",
    "couchbase.sync_gateway.num_goroutines",
    "couchbase.sync_gateway.process_cpu_percent_utilization",
    "couchbase.sync_gateway.process_memory_resident",
    "couchbase.sync_gateway.pub_net_bytes_recv",
    "couchbase.sync_gateway.pub_net_bytes_sent",
    "couchbase.sync_gateway.security.auth_failed_count",
    "couchbase.sync_gateway.security.auth_success_count",
    "couchbase.sync_gateway.security.num_access_errors",
    "couchbase.sync_gateway.security.num_docs_rejected",
    "couchbase.sync_gateway.security.total_auth_time",
    "couchbase.sync_gateway.shared_bucket_import.import_cancel_cas",
    "couchbase.sync_gateway.shared_bucket_import.import_count",
    "couchbase.sync_gateway.shared_bucket_import.import_error_count",
    "couchbase.sync_gateway.shared_bucket_import.import_high_seq",
    "couchbase.sync_gateway.shared_bucket_import.import_partitions",
    "couchbase.sync_gateway.shared_bucket_import.import_processing_time",
    "couchbase.sync_gateway.system_memory_total",
    "couchbase.sync_gateway.warn_count",
]

INDEX_STATS_INDEXER_METRICS = [
    'couchbase.indexer.indexer_state',
    'couchbase.indexer.memory_quota',
    'couchbase.indexer.memory_total_storage',
    'couchbase.indexer.memory_used',
    'couchbase.indexer.total_indexer_gc_pause_ns',
]

INDEX_STATS_GAUGE_METRICS = [
    'couchbase.index.avg_drain_rate',
    'couchbase.index.avg_item_size',
    'couchbase.index.avg_scan_latency',
    'couchbase.index.cache_hit_percent',
    'couchbase.index.data_size',
    'couchbase.index.disk_size',
    'couchbase.index.frag_percent',
    'couchbase.index.initial_build_progress',
    'couchbase.index.last_known_scan_time',
    'couchbase.index.num_docs_pending',
    'couchbase.index.num_docs_queued',
    'couchbase.index.num_pending_requests',
    'couchbase.index.recs_in_mem',
    'couchbase.index.recs_on_disk',
    'couchbase.index.resident_percent',
    'couchbase.index.total_scan_duration',
]

INDEX_STATS_COUNT_METRICS = [
    'couchbase.index.cache_hits',
    'couchbase.index.cache_misses',
    'couchbase.index.items_count',
    'couchbase.index.num_docs_indexed',
    'couchbase.index.num_items_flushed',
    'couchbase.index.num_requests',
    'couchbase.index.num_rows_returned',
    'couchbase.index.num_scan_errors',
    'couchbase.index.num_scan_timeouts',
    'couchbase.index.scan_bytes_read',
]


QUERY_STATS_ALWAYS_PRESENT = {
    'cores',
    'cpu_sys_percent',
    'cpu_user_percent',
    'memory_total',
    'request_per_sec_15min',
    'request_per_sec_1min',
    'request_per_sec_5min',
    'request_prepared_percent',
}
