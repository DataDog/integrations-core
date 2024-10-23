# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

FLY_EDGE_METRICS = {
    'fly_edge_http_responses_count': {'name': 'edge.http_responses', 'type': 'counter'},
    'fly_edge_tcp_connects_count': {'name': 'edge.tcp_connects', 'type': 'counter'},
    'fly_edge_tcp_disconnects_count': {'name': 'edge.tcp_disconnects', 'type': 'counter'},
    'fly_edge_data_out': {'name': 'edge.data_out', 'type': 'counter'},
    'fly_edge_data_in': {'name': 'edge.data_in', 'type': 'counter'},
    'fly_edge_tls_handshake_errors': {'name': 'edge.tls_handshake_errors', 'type': 'counter'},
}

FLY_APP_METRICS = {
    'fly_app_concurrency': {'name': 'app.concurrency', 'type': 'gauge'},
    'fly_app_http_responses_count': {'name': 'app.http_responses', 'type': 'counter'},
    'fly_app_tcp_connects_count': {'name': 'app.tcp_connects', 'type': 'counter'},
    'fly_app_tcp_disconnects_count': {'name': 'app.tcp_disconnects', 'type': 'counter'},
}

FLY_INSTANCE_METRICS = {
    'fly_instance_up': {'name': 'instance.up', 'type': 'gauge'},
    'fly_instance_load_average': {'name': 'instance.load.avg', 'type': 'gauge'},
    'fly_instance_cpu': {'name': 'instance.cpu', 'type': 'counter'},
}

FLY_INSTANCE_MEMORY_METRICS = {
    'fly_instance_memory_mem_total': {'name': 'instance.memory.mem_total', 'type': 'gauge'},
    'fly_instance_memory_mem_free': {'name': 'instance.memory.mem_free', 'type': 'gauge'},
    'fly_instance_memory_mem_available': {'name': 'instance.memory.mem_available', 'type': 'gauge'},
    'fly_instance_memory_buffers': {'name': 'instance.memory.buffers', 'type': 'gauge'},
    'fly_instance_memory_cached': {'name': 'instance.memory.cached', 'type': 'gauge'},
    'fly_instance_memory_swap_cached': {'name': 'instance.memory.swap_cached', 'type': 'gauge'},
    'fly_instance_memory_active': {'name': 'instance.memory.active', 'type': 'gauge'},
    'fly_instance_memory_inactive': {'name': 'instance.memory.inactive', 'type': 'gauge'},
    'fly_instance_memory_swap_total': {'name': 'instance.memory.swap_total', 'type': 'gauge'},
    'fly_instance_memory_swap_free': {'name': 'instance.memory.swap_free', 'type': 'gauge'},
    'fly_instance_memory_dirty': {'name': 'instance.memory.dirty', 'type': 'gauge'},
    'fly_instance_memory_writeback': {'name': 'instance.memory.writeback', 'type': 'gauge'},
    'fly_instance_memory_slab': {'name': 'instance.memory.slab', 'type': 'gauge'},
    'fly_instance_memory_shmem': {'name': 'instance.memory.shmem', 'type': 'gauge'},
    'fly_instance_memory_vmalloc_total': {'name': 'instance.memory.vmalloc_total', 'type': 'gauge'},
    'fly_instance_memory_vmalloc_used': {'name': 'instance.memory.vmalloc_used', 'type': 'gauge'},
    'fly_instance_memory_vmalloc_chunk': {'name': 'instance.memory.vmalloc_chunk', 'type': 'gauge'},
    'fly_instance_memory_pressure_full': {'name': 'instance.memory.pressure_full', 'type': 'gauge'},
    'fly_instance_memory_pressure_some': {'name': 'instance.memory.pressure_some', 'type': 'gauge'},
}

FLY_INSTANCE_DISK_METRICS = {
    'fly_instance_disk_reads_completed': {'name': 'instance.disk.reads_completed', 'type': 'counter'},
    'fly_instance_disk_reads_merged': {'name': 'instance.disk.reads_merged', 'type': 'counter'},
    'fly_instance_disk_sectors_read': {'name': 'instance.disk.sectors_read', 'type': 'counter'},
    'fly_instance_disk_time_reading': {'name': 'instance.disk.time_reading', 'type': 'counter'},
    'fly_instance_disk_writes_completed': {'name': 'instance.disk.writes_completed', 'type': 'counter'},
    'fly_instance_disk_writes_merged': {'name': 'instance.disk.writes_merged', 'type': 'counter'},
    'fly_instance_disk_sectors_written': {'name': 'instance.disk.sectors_written', 'type': 'counter'},
    'fly_instance_disk_time_writing': {'name': 'instance.disk.time_writing', 'type': 'counter'},
    'fly_instance_disk_io_in_progress': {'name': 'instance.disk.io_in_progress', 'type': 'gauge'},
    'fly_instance_disk_time_io': {'name': 'instance.disk.time_io', 'type': 'counter'},
    'fly_instance_disk_time_io_weighted': {'name': 'instance.disk.time_io_weighted', 'type': 'counter'},
}

FLY_INSTANCE_NET_METRICS = {
    'fly_instance_net_recv_bytes': {'name': 'instance.net.recv_bytes', 'type': 'counter'},
    'fly_instance_net_recv_packets': {'name': 'instance.net.recv_packets', 'type': 'counter'},
    'fly_instance_net_recv_errs': {'name': 'instance.net.recv_errs', 'type': 'counter'},
    'fly_instance_net_recv_drop': {'name': 'instance.net.recv_drop', 'type': 'counter'},
    'fly_instance_net_recv_fifo': {'name': 'instance.net.recv_fifo', 'type': 'counter'},
    'fly_instance_net_recv_frame': {'name': 'instance.net.recv_frame', 'type': 'counter'},
    'fly_instance_net_recv_compressed': {'name': 'instance.net.recv_compressed', 'type': 'counter'},
    'fly_instance_net_recv_multicast': {'name': 'instance.net.recv_multicast', 'type': 'counter'},
    'fly_instance_net_sent_bytes': {'name': 'instance.net.sent_bytes', 'type': 'counter'},
    'fly_instance_net_sent_packets': {'name': 'instance.net.sent_packets', 'type': 'counter'},
    'fly_instance_net_sent_errs': {'name': 'instance.net.sent_errs', 'type': 'counter'},
    'fly_instance_net_sent_drop': {'name': 'instance.net.sent_drop', 'type': 'counter'},
    'fly_instance_net_sent_fifo': {'name': 'instance.net.sent_fifo', 'type': 'counter'},
    'fly_instance_net_sent_colls': {'name': 'instance.net.sent_colls', 'type': 'counter'},
    'fly_instance_net_sent_carrier': {'name': 'instance.net.sent_carrier', 'type': 'counter'},
    'fly_instance_net_sent_compressed': {'name': 'instance.net.sent_compressed', 'type': 'counter'},
}

FLY_INSTANCE_FILEFD_METRICS = {
    'fly_instance_filefd_allocated': {'name': 'instance.filefd.allocated', 'type': 'gauge'},
    'fly_instance_filefd_maximum': {'name': 'instance.filefd.max', 'type': 'gauge'},
}

FLY_INSTANCE_FILESYSTEM_METRICS = {
    'fly_instance_filesystem_blocks': {'name': 'instance.filesystem.blocks', 'type': 'gauge'},
    'fly_instance_filesystem_block_size': {'name': 'instance.filesystem.block_size', 'type': 'gauge'},
    'fly_instance_filesystem_blocks_free': {'name': 'instance.filesystem.blocks_free', 'type': 'gauge'},
    'fly_instance_filesystem_blocks_avail': {'name': 'instance.filesystem.blocks_avail', 'type': 'gauge'},
}

FLY_INSTANCE_VOLUME_METRICS = {
    'fly_volume_size_bytes': {'name': 'volume.size', 'type': 'gauge'},
    'fly_volume_used_pct': {'name': 'volume.used', 'type': 'gauge'},
}

FLY_POSTGRES_METRICS = {
    'pg_stat_activity_count': {'name': 'pg_stat.activity_count', 'type': 'counter'},
    'pg_stat_activity_max_tx_duration': {'name': 'pg_stat.activity.max_tx_duration', 'type': 'gauge'},
    'pg_stat_archiver_archived_count': {'name': 'pg_stat.archiver.archived_count', 'type': 'counter'},
    'pg_stat_archiver_failed_count': {'name': 'pg_stat.archiver.failed_count', ' type': 'counter'},
    'pg_stat_bgwriter_buffers_alloc': {'name': 'pg_stat.bgwriter.buffers_alloc', 'type': 'counter'},
    'pg_stat_bgwriter_buffers_backend_fsync': {'name': 'pg_stat.bgwriter.buffers_backend_fsync', 'type': 'counter'},
    'pg_stat_bgwriter_buffers_backend': {'name': 'pg_stat.bgwriter.buffers_backend', 'type': 'counter'},
    'pg_stat_bgwriter_buffers_checkpoint': {'name': 'pg_stat.bgwriter.buffers_checkpoint', 'type': 'counter'},
    'pg_stat_bgwriter_buffers_clean': {'name': 'pg_stat.bgwriter.buffers_clean', 'type': 'counter'},
    'pg_stat_bgwriter_checkpoint_sync_time': {'name': 'pg_stat.bgwriter.checkpoint_sync_time', 'type': 'counter'},
    'pg_stat_bgwriter_checkpoint_write_time': {'name': 'pg_stat.bgwriter.checkpoint_write_time', 'type': 'counter'},
    'pg_stat_bgwriter_checkpoints_req': {'name': 'pg_stat.bgwriter.checkpoints_req', 'type': 'counter'},
    'pg_stat_bgwriter_checkpoints_timed': {'name': 'pg_stat.bgwriter.checkpoints_timed', 'type': 'counter'},
    'pg_stat_bgwriter_maxwritten_clean': {'name': 'pg_stat.bgwriter.maxwritten_clean', 'type': 'counter'},
    'pg_stat_bgwriter_stats_reset': {'name': 'pg_stat.bgwriter.stats_reset', 'type': 'counter'},
    'pg_stat_database_blk_read_time': {'name': 'pg_stat.database.blk_read_time', 'type': 'counter'},
    'pg_stat_database_blk_write_time': {'name': 'pg_stat.database.blk_write_time', 'type': 'counter'},
    'pg_stat_database_blks_hit': {'name': 'pg_stat.database.blks_hit', 'type': 'counter'},
    'pg_stat_database_blks_read': {'name': 'pg_stat.database.blks_read', 'type': 'counter'},
    'pg_stat_database_conflicts_confl_bufferpin': {
        'name': 'pg_stat.database.conflicts_confl_bufferpin',
        'type': 'counter',
    },
    'pg_stat_database_conflicts_confl_deadlock': {
        'name': 'pg_stat.database.conflicts_confl_deadlock',
        'type': 'counter',
    },
    'pg_stat_database_conflicts_confl_lock': {'name': 'pg_stat.database.conflicts_confl_lock', 'type': 'counter'},
    'pg_stat_database_conflicts_confl_snapshot': {
        'name': 'pg_stat.database.conflicts_confl_snapshot',
        'type': 'counter',
    },
    'pg_stat_database_conflicts_confl_tablespace': {
        'name': 'pg_stat.database.conflicts_confl_tablespace',
        'type': 'counter',
    },
    'pg_stat_database_conflicts': {'name': 'pg_stat.database.conflicts', 'type': 'counter'},
    'pg_stat_database_deadlocks': {'name': 'pg_stat.database.deadlocks', 'type': 'counter'},
    'pg_stat_database_numbackends': {'name': 'pg_stat.database.numbackends', 'type': 'gauge'},
    'pg_stat_database_stats_reset': {'name': 'pg_stat.database.stats_reset', 'type': 'counter'},
    'pg_stat_database_tup_deleted': {'name': 'pg_stat.database.tup_deleted', 'type': 'counter'},
    'pg_stat_database_tup_fetched': {'name': 'pg_stat.database.tup_fetched', 'type': 'counter'},
    'pg_stat_database_tup_inserted': {'name': 'pg_stat.database.tup_inserted', 'type': 'counter'},
    'pg_stat_database_tup_returned': {'name': 'pg_stat.database.tup_returned', 'type': 'counter'},
    'pg_stat_database_tup_updated': {'name': 'pg_stat.database.tup_updated', 'type': 'counter'},
    'pg_stat_database_xact_commit': {'name': 'pg_stat.database.xact_commit', 'type': 'counter'},
    'pg_stat_database_xact_rollback': {'name': 'pg_stat.database.xact_rollback', 'type': 'counter'},
    'pg_stat_replication_pg_current_wal_lsn_bytes': {
        'name': 'pg_stat.replication.pg_current_wal_lsn_bytes',
        'type': 'gauge',
    },
    'pg_stat_replication_pg_wal_lsn_diff': {'name': 'pg_stat.replication.pg_wal_lsn_diff', 'type': 'gauge'},
    'pg_stat_replication_reply_time': {'name': 'pg_stat.replication.reply_time', 'type': 'gauge'},
    'pg_replication_lag': {'name': 'pg.replication.lag', 'type': 'gauge'},
    'pg_database_size_bytes': {'name': 'pg.database.size', 'type': 'gauge'},
}

METRICS = {
    **FLY_EDGE_METRICS,
    **FLY_APP_METRICS,
    **FLY_INSTANCE_METRICS,
    **FLY_INSTANCE_MEMORY_METRICS,
    **FLY_INSTANCE_DISK_METRICS,
    **FLY_INSTANCE_NET_METRICS,
    **FLY_INSTANCE_FILEFD_METRICS,
    **FLY_INSTANCE_FILESYSTEM_METRICS,
    **FLY_INSTANCE_VOLUME_METRICS,
    **FLY_POSTGRES_METRICS,
}

HISTOGRAM_METRICS = {
    'fly_edge_http_response_time_seconds_count': 'edge.http_response_time.count',
    'fly_edge_http_response_time_seconds_sum': 'edge.http_response_time.sum',
    'fly_edge_http_response_time_seconds_bucket': 'edge.http_response_time.bucket',
    'fly_edge_tls_handshake_time_seconds_bucket': 'edge.tls_handshake_time.bucket',
    'fly_edge_tls_handshake_time_seconds_count': 'edge.tls_handshake_time.count',
    'fly_edge_tls_handshake_time_seconds_sum': 'edge.tls_handshake_time.sum',
    'fly_app_http_response_time_seconds_bucket': 'app.http_response_time.bucket',
    'fly_app_http_response_time_seconds_count': 'app.http_response_time.count',
    'fly_app_http_response_time_seconds_sum': 'app.http_response_time.sum',
    'fly_app_connect_time_seconds_bucket': 'app.connect_time.bucket',
    'fly_app_connect_time_seconds_count': 'app.connect_time.count',
    'fly_app_connect_time_seconds_sum': 'app.connect_time.sum',
}

RENAME_LABELS_MAP = {
    'app': 'app_name',
    'region': 'fly_region',
    'host': 'fly_hypervisor_id',
    'mount': 'fly_mount',
    'instance': 'app_instance_id',
    'le': 'upper_bound',
    'version': 'tls_version',
}
