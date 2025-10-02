DEFAULT_MAX_SLOW_ENTRIES = 128
MAX_SLOW_ENTRIES_KEY = "slowlog-max-len"

REPL_KEY = 'master_link_status'
LINK_DOWN_KEY = 'master_link_down_since_seconds'

DEFAULT_CLIENT_NAME = "unknown"

CONFIG_GAUGE_KEYS = {
    'maxclients': 'redis.net.maxclients',
}

GAUGE_KEYS = {
    # Server
    'io_threads_active': 'redis.server.io_threads_active',
    # Active defrag metrics
    'active_defrag_running': 'redis.active_defrag.running',
    'active_defrag_hits': 'redis.active_defrag.hits',
    'active_defrag_misses': 'redis.active_defrag.misses',
    'active_defrag_key_hits': 'redis.active_defrag.key_hits',
    'active_defrag_key_misses': 'redis.active_defrag.key_misses',
    # Append-only metrics
    'aof_last_rewrite_time_sec': 'redis.aof.last_rewrite_time',
    'aof_rewrite_in_progress': 'redis.aof.rewrite',
    'aof_current_size': 'redis.aof.size',
    'aof_buffer_length': 'redis.aof.buffer_length',
    'loading_total_bytes': 'redis.aof.loading_total_bytes',
    'loading_loaded_bytes': 'redis.aof.loading_loaded_bytes',
    'loading_loaded_perc': 'redis.aof.loading_loaded_perc',
    'loading_eta_seconds': 'redis.aof.loading_eta_seconds',
    # Network
    'connected_clients': 'redis.net.clients',
    'connected_slaves': 'redis.net.slaves',
    'rejected_connections': 'redis.net.rejected',
    # clients
    'blocked_clients': 'redis.clients.blocked',
    'client_biggest_input_buf': 'redis.clients.biggest_input_buf',
    'client_longest_output_list': 'redis.clients.longest_output_list',
    'client_recent_max_input_buffer': 'redis.clients.recent_max_input_buffer',
    'client_recent_max_output_buffer': 'redis.clients.recent_max_output_buffer',
    # Keys
    'evicted_keys': 'redis.keys.evicted',
    'expired_keys': 'redis.keys.expired',
    # stats
    'latest_fork_usec': 'redis.perf.latest_fork_usec',
    'bytes_received_per_sec': 'redis.bytes_received_per_sec',
    'bytes_sent_per_sec': 'redis.bytes_sent_per_sec',
    # Note: 'bytes_received_per_sec' and 'bytes_sent_per_sec' are only
    # available on Azure Redis
    'instantaneous_input_kbps': 'redis.net.instantaneous_input',
    'instantaneous_output_kbps': 'redis.net.instantaneous_output',
    'total_connections_received': 'redis.net.total_connections_received',
    # pubsub
    'pubsub_channels': 'redis.pubsub.channels',
    'pubsub_patterns': 'redis.pubsub.patterns',
    # rdb
    'rdb_bgsave_in_progress': 'redis.rdb.bgsave',
    'rdb_changes_since_last_save': 'redis.rdb.changes_since_last',
    'rdb_last_bgsave_time_sec': 'redis.rdb.last_bgsave_time',
    # memory
    'mem_fragmentation_bytes': 'redis.mem.fragmentation',
    'mem_fragmentation_ratio': 'redis.mem.fragmentation_ratio',
    'mem_total_replication_buffers': 'redis.mem.total_replication_buffers',
    'mem_clients_slaves': 'redis.mem.clients_slaves',
    'mem_clients_normal': 'redis.mem.clients_normal',
    'used_memory': 'redis.mem.used',
    'used_memory_lua': 'redis.mem.lua',
    'used_memory_peak': 'redis.mem.peak',
    'used_memory_rss': 'redis.mem.rss',
    'used_memory_startup': 'redis.mem.startup',
    'used_memory_overhead': 'redis.mem.overhead',
    'used_memory_dataset': 'redis.mem.dataset',
    'used_memory_vm_eval': 'redis.mem.vm_eval',
    'used_memory_vm_functions': 'redis.mem.vm_functions',
    'used_memory_vm_total': 'redis.mem.vm_total',
    'used_memory_functions': 'redis.mem.functions',
    'used_memory_scripts_eval': 'redis.mem.scripts_eval',
    'used_memory_scripts': 'redis.mem.scripts',
    'maxmemory': 'redis.mem.maxmemory',
    # replication
    'master_last_io_seconds_ago': 'redis.replication.last_io_seconds_ago',
    'master_sync_in_progress': 'redis.replication.sync',
    'master_sync_left_bytes': 'redis.replication.sync_left_bytes',
    'repl_backlog_histlen': 'redis.replication.backlog_histlen',
    'master_repl_offset': 'redis.replication.master_repl_offset',
    'slave_repl_offset': 'redis.replication.slave_repl_offset',
    'total_net_repl_input_bytes': 'redis.replication.input_total_bytes',
    'total_net_repl_output_bytes': 'redis.replication.output_total_bytes',
}

RATE_KEYS = {
    # cpu
    'used_cpu_sys': 'redis.cpu.sys',
    'used_cpu_sys_children': 'redis.cpu.sys_children',
    'used_cpu_user': 'redis.cpu.user',
    'used_cpu_user_children': 'redis.cpu.user_children',
    'used_cpu_sys_main_thread': 'redis.cpu.sys_main_thread',
    'used_cpu_user_main_thread': 'redis.cpu.user_main_thread',
    # stats
    'keyspace_hits': 'redis.stats.keyspace_hits',
    'keyspace_misses': 'redis.stats.keyspace_misses',
    'io_threaded_reads_processed': 'redis.stats.io_threaded_reads_processed',
    'io_threaded_writes_processed': 'redis.stats.io_threaded_writes_processed',
}

