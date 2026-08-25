# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

METRIC_MAP = {
    # TYPE falcosecurity_evt_hostname_info gauge
    'falcosecurity_evt_hostname_info': 'evt.hostname',
    # TYPE falcosecurity_falco_container_memory_used_bytes gauge
    'falcosecurity_falco_container_memory_used_bytes': 'container.memory.used',
    # TYPE falcosecurity_falco_cpu_usage_ratio gauge
    'falcosecurity_falco_cpu_usage_ratio': 'cpu.usage.ratio',
    # TYPE falcosecurity_falco_duration_seconds_total counter
    'falcosecurity_falco_duration_seconds': 'duration.seconds',
    # TYPE falcosecurity_falco_evt_source_info gauge
    'falcosecurity_falco_evt_source_info': 'evt.source',
    # TYPE falcosecurity_falco_host_cpu_usage_ratio gauge
    'falcosecurity_falco_host_cpu_usage_ratio': 'host.cpu.usage.ratio',
    # TYPE falcosecurity_falco_host_memory_used_bytes gauge
    'falcosecurity_falco_host_memory_used_bytes': 'host.memory.used',
    # TYPE falcosecurity_falco_host_num_cpus_total gauge
    'falcosecurity_falco_host_num_cpus_total': 'host.num.cpus',
    # TYPE falcosecurity_falco_host_open_fds_total gauge
    'falcosecurity_falco_host_open_fds_total': 'host.open.fds',
    # TYPE falcosecurity_falco_host_procs_running_total gauge
    'falcosecurity_falco_host_procs_running_total': 'host.procs.running',
    # TYPE falcosecurity_falco_jemalloc_active_bytes counter
    'falcosecurity_falco_jemalloc_active_bytes': 'jemalloc.active',
    # TYPE falcosecurity_falco_jemalloc_allocated_bytes counter
    'falcosecurity_falco_jemalloc_allocated_bytes': 'jemalloc.allocated',
    # TYPE falcosecurity_falco_jemalloc_mapped_bytes counter
    'falcosecurity_falco_jemalloc_mapped_bytes': 'jemalloc.mapped',
    # TYPE falcosecurity_falco_jemalloc_metadata_bytes counter
    'falcosecurity_falco_jemalloc_metadata_bytes': 'jemalloc.metadata',
    # TYPE falcosecurity_falco_jemalloc_metadata_thp_bytes counter
    'falcosecurity_falco_jemalloc_metadata_thp_bytes': 'jemalloc.metadata.thp',
    # TYPE falcosecurity_falco_jemalloc_resident_bytes counter
    'falcosecurity_falco_jemalloc_resident_bytes': 'jemalloc.resident',
    # TYPE falcosecurity_falco_jemalloc_retained_bytes counter
    'falcosecurity_falco_jemalloc_retained_bytes': 'jemalloc.retained',
    # TYPE falcosecurity_falco_jemalloc_zero_reallocs_bytes counter
    'falcosecurity_falco_jemalloc_zero_reallocs_bytes': 'jemalloc.zero.reallocs',
    # TYPE falcosecurity_falco_kernel_release_info gauge
    'falcosecurity_falco_kernel_release_info': 'kernel.release',
    # TYPE falcosecurity_falco_memory_pss_bytes gauge
    'falcosecurity_falco_memory_pss_bytes': 'memory.pss',
    # TYPE falcosecurity_falco_memory_rss_bytes gauge
    'falcosecurity_falco_memory_rss_bytes': 'memory.rss',
    # TYPE falcosecurity_falco_memory_vsz_bytes gauge
    'falcosecurity_falco_memory_vsz_bytes': 'memory.vsz',
    # TYPE falcosecurity_falco_outputs_queue_num_drops_total counter
    'falcosecurity_falco_outputs_queue_num_drops': 'outputs.queue.num.drops',
    # TYPE falcosecurity_falco_rules_matches_total counter
    'falcosecurity_falco_rules_matches': 'rules.matches',
    # TYPE falcosecurity_falco_sha256_config_files_info gauge
    'falcosecurity_falco_sha256_config_files_info': 'sha256.config.files',
    # TYPE falcosecurity_falco_sha256_rules_files_info gauge
    'falcosecurity_falco_sha256_rules_files_info': 'sha256.rules.files',
    # TYPE falcosecurity_scap_engine_name_info gauge
    'falcosecurity_scap_engine_name_info': 'scap.engine.name',
    # TYPE falcosecurity_scap_n_added_fds_total counter
    'falcosecurity_scap_n_added_fds': 'scap.n.added.fds',
    # TYPE falcosecurity_scap_n_added_threads_total counter
    'falcosecurity_scap_n_added_threads': 'scap.n.added.threads',
    # TYPE falcosecurity_scap_n_cached_fd_lookups_total counter
    'falcosecurity_scap_n_cached_fd_lookups': 'scap.n.cached.fd.lookups',
    # TYPE falcosecurity_scap_n_cached_thread_lookups_total counter
    'falcosecurity_scap_n_cached_thread_lookups': 'scap.n.cached.thread.lookups',
    # TYPE falcosecurity_scap_n_containers_total gauge
    'falcosecurity_scap_n_containers_total': 'scap.n.containers',
    # TYPE falcosecurity_scap_n_drops_buffer_total counter
    'falcosecurity_scap_n_drops_buffer': 'scap.n.drops.buffer',
    # TYPE falcosecurity_scap_n_drops_full_threadtable_total counter
    'falcosecurity_scap_n_drops_full_threadtable': 'scap.n.drops.full.threadtable',
    # TYPE falcosecurity_scap_n_drops_scratch_map_total counter
    'falcosecurity_scap_n_drops_scratch_map': 'scap.n.drops.scratch.map',
    # TYPE falcosecurity_scap_n_drops_total counter
    'falcosecurity_scap_n_drops': 'scap.n.drops',
    # TYPE falcosecurity_scap_n_evts_total counter
    'falcosecurity_scap_n_evts': 'scap.n.evts',
    # TYPE falcosecurity_scap_n_failed_fd_lookups_total counter
    'falcosecurity_scap_n_failed_fd_lookups': 'scap.n.failed.fd.lookups',
    # TYPE falcosecurity_scap_n_failed_thread_lookups_total counter
    'falcosecurity_scap_n_failed_thread_lookups': 'scap.n.failed.thread.lookups',
    # TYPE falcosecurity_scap_n_fds_total gauge
    'falcosecurity_scap_n_fds_total': 'scap.n.fds',
    # TYPE falcosecurity_scap_n_missing_container_images_total gauge
    'falcosecurity_scap_n_missing_container_images_total': 'scap.n.missing.container.images',
    # TYPE falcosecurity_scap_n_noncached_fd_lookups_total counter
    'falcosecurity_scap_n_noncached_fd_lookups': 'scap.n.noncached.fd.lookups',
    # TYPE falcosecurity_scap_n_noncached_thread_lookups_total counter
    'falcosecurity_scap_n_noncached_thread_lookups': 'scap.n.noncached.thread.lookups',
    # TYPE falcosecurity_scap_n_removed_fds_total counter
    'falcosecurity_scap_n_removed_fds': 'scap.n.removed.fds',
    # TYPE falcosecurity_scap_n_removed_threads_total counter
    'falcosecurity_scap_n_removed_threads': 'scap.n.removed.threads',
    # TYPE falcosecurity_scap_n_retrieve_evts_drops_total counter
    'falcosecurity_scap_n_retrieve_evts_drops': 'scap.n.retrieve.evts.drops',
    # TYPE falcosecurity_scap_n_retrieved_evts_total counter
    'falcosecurity_scap_n_retrieved_evts': 'scap.n.retrieved.evts',
    # TYPE falcosecurity_scap_n_store_evts_drops_total counter
    'falcosecurity_scap_n_store_evts_drops': 'scap.n.store.evts.drops',
    # TYPE falcosecurity_scap_n_stored_evts_total counter
    'falcosecurity_scap_n_stored_evts': 'scap.n.stored.evts',
    # TYPE falcosecurity_scap_n_threads_total gauge
    'falcosecurity_scap_n_threads_total': 'scap.n.threads',
}

# TYPE falcosecurity_falco_version_info gauge
FALCO_VERSION = {'falcosecurity_falco_version_info': {'type': 'metadata', 'label': 'version', 'name': 'version'}}

METRIC_MAP.update(FALCO_VERSION)

RENAME_LABELS = {
    'version': 'falco_version',
    'hostname': 'falco_hostname',
}
