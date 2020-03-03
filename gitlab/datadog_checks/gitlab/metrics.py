METRICS_MAP = {
  "gitlab_banzai_cached_render_real_duration_seconds_count": "banzai.cached_render_real_duration.count",
  "gitlab_banzai_cached_render_real_duration_seconds_sum": "banzai_cached_render_real_duration.sum"
  "gitlab_banzai_cacheless_render_real_duration_seconds_count", "banzai.cacheless_render_real_duration.count",
  "gitlab_banzai_cacheless_render_real_duration_seconds_sum": "banzai.cacheless_render_real_duration.sum"
  "gitlab_cache_misses_total": "cache.misses_total",
  "gitlab_cache_operation_duration_seconds_count": "cache.operation_duration.count",
  "gitlab_cache_operation_duration_seconds_sum": "cache.operation_duration.sum",
  "gitlab_cache_operations_total": "cache_operations_total",
  "gitlab_database_transaction_seconds_count": "database.transaction_duration.count",
  "gitlab_database_transaction_seconds_sum": "database.transaction_seconds.sum",
  "gitlab_method_call_duration_seconds_count": "method_call_duration.count",
  "gitlab_method_call_duration_seconds_sum": "method_call_duration.sum",
  "gitlab_page_out_of_bounds": "page_out_of_bounds",
  "gitlab_rails_queue_duration_seconds_count": "rails.queue_duration.count",
  "gitlab_rails_queue_duration_seconds_sum": "rails.queue_duration.sum",
  "gitlab_sql_duration_seconds_count": "sql.duration.count",
  "gitlab_sql_duration_seconds_sum": "sql.duration.sum",
  "gitlab_transaction_allocated_memory_bytes_count": "transaction.allocated_memory.count",
  "gitlab_transaction_allocated_memory_bytes_sum": "transaction.allocated_memory.sum",
  "gitlab_transaction_cache_count_total": "transaction.cache_count_total",
  "gitlab_transaction_cache_duration_total": "transaction.cache_duration_total",
  "gitlab_transaction_cache_read_hit_count_total": "transaction.cache_read_hit_count_total",
  "gitlab_transaction_cache_read_miss_count_total": "transaction.cache_read_miss_count_total",
  "gitlab_transaction_duration_seconds_count": "transaction.duration.count",
  "gitlab_transaction_duration_seconds_sum": "transaction_duration.sum",
  "gitlab_transaction_event_build_found_total": "transaction.event_build_found_total",
  "gitlab_transaction_event_build_invalid_total": "transaction.event_build_invalid_total",
  "gitlab_transaction_event_build_not_found_cached_total": "transaction.event_build_not_found_cached_total",
  "gitlab_transaction_event_build_not_found_total": "transaction.event_build_not_found_total",
  "gitlab_transaction_event_change_default_branch_total": "transaction.event_change_default_branch_total",
  "gitlab_transaction_event_create_repository_total": "transaction.event_create_repository_total",
  "gitlab_transaction_event_etag_caching_cache_hit_total": "transaction.event_etag_caching_cache_hit_total",
  "gitlab_transaction_event_etag_caching_header_missing_total": "transaction.event_etag_caching_header_missing_total",
  "gitlab_transaction_event_etag_caching_key_not_found_total": "transaction.event_etag_caching_key_not_found_total",
  "gitlab_transaction_event_etag_caching_middleware_used_total": "transaction.event_etag_caching_middleware_used_total",
  "gitlab_transaction_event_etag_caching_resource_changed_total": "transaction.event_etag_caching_resource_changed_total",
  "gitlab_transaction_event_fork_repository_total": "transaction.event_fork_repository_total",
  "gitlab_transaction_event_import_repository_total": "transaction.event_import_repository_total",
  "gitlab_transaction_event_push_branch_total": "transaction.event_push_branch_total",
  "gitlab_transaction_event_push_commit_total": "transaction.event_push_commit_total",
  "gitlab_transaction_event_push_tag_total": "transaction.event_push_tag_total",
  "gitlab_transaction_event_rails_exception_total": "transaction.event_rails_exception_total",
  "gitlab_transaction_event_receive_email_total": "transaction.event_receive_email_total",
  "gitlab_transaction_event_remote_mirrors_failed_total": "transaction.event_remote_mirrors_failed_total",
  "gitlab_transaction_event_remote_mirrors_finished_total": "transaction.event_remote_mirrors_finished_total",
  "gitlab_transaction_event_remote_mirrors_running_total": "transaction.event_remote_mirrors_running_total",
  "gitlab_transaction_event_remove_branch_total": "transaction.event_remove_branch_total",
  "gitlab_transaction_event_remove_repository_total": "transaction.event_remove_repository_total",
  "gitlab_transaction_event_remove_tag_total": "transaction.event_remove_tag_total",
  "gitlab_transaction_event_sidekiq_exception_total": "transaction.event_sidekiq_exception_total",
  "gitlab_transaction_event_stuck_import_jobs_total": "transactionevent_stuck_import_jobs_total",
  "gitlab_transaction_event_update_build_total": "transaction.event_update_build_total",
  "gitlab_transaction_new_redis_connections_total": "transaction.new_redis_connections_total",
  "gitlab_transaction_queue_duration_total": "transaction.queue_duration_total",
  "gitlab.transaction_rails_queue_duration_total": "transaction.rails_queue_duration_total",
  "gitlab.transaction_view_duration_total": "transaction.view_duration_total",
  "gitlab.transaction_view_duration_total_sum": "transaction.view_duration_total.sum",
  "gitlab.view_rendering_duration_seconds_count": "view_rendering_duration_seconds.count",
  "gitlab.view_rendering_duration_seconds_sum": "view_rendering_duration_seconds_sum",
  "http_requests_total": "http_requests_total",
  "http_request_duration_seconds_sum": "http_request_duration_seconds.sum",
  "http_request_duration_seconds_count": "http_request_duration_seconds.count",
  "pipelines_created_total": "pipelines_created_total",
  "rack_uncaught_errors_total": "rack_uncaught_errors_total",
  "user_session_logins_total": "user_session_logins_total",
  "upload_file_does_not_exist": "upload_file_does_not_exist",
  "failed_login_captcha_total": "failed_login_captcha_total",
  "successful_login_captcha_total": "successful_login_captcha_total",
  "auto_devops_pipelines_completed_total": "auto_devops_pipelines_completed_total",
  "sidekiq_jobs_cpu_seconds_count": "sidekiq.jobs_cpu_seconds.count",
  "sidekiq_jobs_cpu_seconds_sum": "sidekiq.jobs_cpu_seconds.sum",
  "sidekiq_jobs_completion_seconds_count": "sidekiq.jobs_completion_seconds.count",
  "sidekiq_jobs_completion_seconds_sum": "sidekiq.jobs_completion_seconds.sum",
  "sidekiq_jobs_queue_duration_seconds_count": "sidekiq.jobs_queue_duration_seconds.count",
  "sidekiq_jobs_queue_duration_seconds_sum": "sidekiq.jobs_queue_duration_seconds.sum",
  "sidekiq_jobs_failed_total": "sidekiq.jobs_failed_total",
  "sidekiq_jobs_retried_total": "sidekiq.jobs_retried_total",
  "sidekiq_running_jobs": "sidekiq.running_jobs",
  "sidekiq_concurrency": "sidekiq.concurrency",
  "ruby_gc_duration_seconds": "ruby_gc_duration_seconds"


gitlab.ruby_file_descriptors,gauge,,,,File descriptors per process,0,gitlab,ruby file descriptors
gitlab.ruby_memory_bytes,gauge,,byte,,Memory usage by process,0,gitlab,ruby memory process
gitlab.ruby_sampler_duration_seconds,count,,second,,Time spent collecting stats,0,gitlab,ruby sampler dur
gitlab.ruby_process_cpu_seconds_total,gauge,,second,,Total amount of CPU time per process,0,gitlab,ruby cpu process
gitlab.ruby_process_max_fds,gauge,,,,Maximum number of open file descriptors per process,0,gitlab,ruby max fds
gitlab.ruby_process_resident_memory_bytes,gauge,,byte,,Memory usage by process,0,gitlab,ruby memory
gitlab.ruby_process_start_time_seconds,gauge,,second,,UNIX timestamp of process start time,0,gitlab,ruby start
gitlab.ruby_gc_stat_count,gauge,,,,Number of ruby garbage collectors,0,gitlab,ruby gc count
gitlab.ruby_gc_stat_heap_allocated_pages,gauge,,page,,Number of currently allocated heap pages,0,gitlab,ruby gc allocated pages
gitlab.ruby_gc_stat_heap_sorted_length,gauge,,,,Length of the heap in memory,0,gitlab,ruby gc heap length
gitlab.ruby_gc_stat_heap_allocatable_pages,gauge,,page,,Number malloced pages that can be used,0,gitlab,ruby gc heap allocatable
gitlab.ruby_gc_stat_heap_available_slots,gauge,,,,Number of slots in heap pages,0,gitlab,ruby gc heap slots
gitlab.ruby_gc_stat_heap_live_slots,gauge,,,,Number of live slots in heap,0,gitlab,ruby gc heap live slots
gitlab.ruby_gc_stat_heap_free_slots,gauge,,,,Number of empty slots in heap,0,gitlab,ruby gc heap live slots
gitlab.ruby_gc_stat_heap_final_slots,gauge,,,,Number of slots in heap with finalizers,0,gitlab,ruby gc heap final slots
gitlab.ruby_gc_stat_heap_marked_slots,gauge,,page,,"Number of slots that are marked, or old",0,gitlab,ruby gc heap marked slots
gitlab.ruby_gc_stat_heap_eden_pages,gauge,,page,,Number of heap pages that contain a live object,0,gitlab,ruby gc heap eden pages
gitlab.ruby_gc_stat_heap_tomb_pages,gauge,,page,,Number of heap pages that do not contain a live object,0,gitlab,ruby gc heap tomb pages
gitlab.ruby_gc_stat_total_allocated_pages,gauge,,page,,Number of pages allocated,0,gitlab,ruby gc heap allocated pages
gitlab.ruby_gc_stat_total_freed_pages,gauge,,page,,Number of pages freed,0,gitlab,ruby gc heap freed pages
gitlab.ruby_gc_stat_total_allocated_objects,gauge,,,,Number of allocated objects,0,gitlab,ruby gc allocated objects
gitlab.ruby_gc_stat_total_freed_objects,gauge,,,,Number of freed objects,0,gitlab,ruby gc freed objects
gitlab.ruby_gc_stat_malloc_increase_bytes,gauge,,byte,,Number of bytes allocated outside of the heap,0,gitlab,ruby gc malloc increase
gitlab.ruby_gc_stat_malloc_increase_bytes_limit,gauge,,byte,,The limit to how many bytes can be allocated outside of the heap,0,gitlab,ruby gc malloc increase lim
gitlab.ruby_gc_stat_minor_gc_count,gauge,,garbage collection,,Number of minor garbage collectors,0,gitlab,ruby gc minor
gitlab.ruby_gc_stat_major_gc_count,gauge,,garbage collection,,Number of major garbage collectors,0,gitlab,ruby gc major
gitlab.ruby_gc_stat_remembered_wb_unprotected_objects,gauge,,,,Number of old objects that reference new objects,0,gitlab,ruby gc wb objects
gitlab.ruby_gc_stat_remembered_wb_unprotected_objects_limit,gauge,,,,The limit of wb ubprotected objects,0,gitlab,ruby gc wb objects lim
gitlab.ruby_gc_stat_old_objects,gauge,,,,The number of old objects,0,gitlab,ruby gc old objects
gitlab.ruby_gc_stat_old_objects_limit,gauge,,,,The limit of number of old objects,0,gitlab,ruby gc old objects lim
gitlab.ruby_gc_stat_oldmalloc_increase_bytes,gauge,,byte,,Number of bytes allocated outside of the heap for old objects,0,gitlab,ruby gc old increase
gitlab.ruby_gc_stat_oldmalloc_increase_bytes_limit,gauge,,byte,,The limit of how many bytes can be allocated outside of the heap for old objects,0,gitlab,ruby gc old increase lim
gitlab.geo_db_replication_lag_seconds,gauge,,second,,Database replication lag (seconds),-1,gitlab,db replication lag
gitlab.geo_repositories,gauge,,,,Total number of repositories available on primary,0,gitlab,db repos
gitlab.geo_repositories_synced,gauge,,,,Number of repositories synced on secondary,0,gitlab,db repos synced
gitlab.geo_repositories_failed,gauge,,,,Number of repositories failed to sync on secondary,-1,gitlab,db repos failed
gitlab.geo_lfs_objects,gauge,,,,Total number of LFS objects available on primary,0,gitlab,db lfs objects
gitlab.geo_lfs_objects_synced,gauge,,,,Number of LFS objects synced on secondary,0,gitlab,db lfs objects synced
gitlab.geo_lfs_objects_failed,gauge,,,,Number of LFS objects failed to sync on secondary,0,gitlab,db lfs objects failed
gitlab.geo_attachments,gauge,,,,Total number of file attachments available on primary,0,gitlab,db attachments
gitlab.geo_attachments_synced,gauge,,,,Number of attachments synced on secondary,0,gitlab,db attachments synced
gitlab.geo_attachments_failed,gauge,,,,Number of attachments failed to sync on secondary,0,gitlab,db attachments failed
gitlab.geo_last_event_id,gauge,,,,Database ID of the latest event log entry on the primary,0,gitlab,db last id
gitlab.geo_last_event_timestamp,gauge,,,,UNIX timestamp of the latest event log entry on the primary,0,gitlab,db last timestamp
gitlab.geo_cursor_last_event_id,gauge,,,,Last database ID of the event log processed by the secondary,0,gitlab,db last curser id
gitlab.geo_cursor_last_event_timestamp,gauge,,,,Last UNIX timestamp of the event log processed by the secondary,0,gitlab,db last curser timestamp
gitlab.geo_status_failed_total,count,,,,Number of times retrieving the status from the Geo Node failed,-1,gitlab,db fail status
gitlab.geo_last_successful_status_check_timestamp,gauge,,,,Last timestamp when the status was successfully updated,0,gitlab,db success last timestamp
gitlab.geo_lfs_objects_synced_missing_on_primary,gauge,,,,Number of LFS objects marked as synced due to the file missing on the primary,-1,gitlab,db lfs object missing
gitlab.geo_job_artifacts_synced_missing_on_primary,gauge,,,,Number of job artifacts marked as synced due to the file missing on the primary,-1,gitlab,db lfs artifact missing
gitlab.geo_attachments_synced_missing_on_primary,gauge,,,,Number of attachments marked as synced due to the file missing on the primary,-1,gitlab,db lfs attachment missing
gitlab.geo_repositories_checksummed_count,gauge,,,,Number of repositories checksummed on primary,0,gitlab,db repos checksummed
gitlab.geo_repositories_checksum_failed_count,gauge,,,,Number of repositories failed to calculate the checksum on primary,-1,gitlab,db repos checksum failed
gitlab.geo_wikis_checksummed_count,gauge,,,,Number of wikis checksummed on primary,0,gitlab,db wikis checksummed
gitlab.geo_wikis_checksum_failed_count,gauge,,,,Number of wikis failed to calculate the checksum on primary,-1,gitlab,db wikis checksum failed
gitlab.geo_repositories_verified_count,gauge,,,,Number of repositories verified on secondary,0,gitlab,db repos verified
gitlab.geo_repositories_verification_failed_count,gauge,,,,Number of repositories failed to verify on secondary,-1,gitlab,db repos failed
gitlab.geo_repositories_checksum_mismatch_count,gauge,,,,Number of repositories that checksum mismatch on secondary,-1,gitlab,db repos checksum mismatch
gitlab.geo_wikis_verified_count,gauge,,,,Number of wikis verified on secondary,0,gitlab,db wikis verified
gitlab.geo_wikis_verification_failed_count,gauge,,,,Number of wikis failed to verify on secondary,-1,gitlab,db wikis verified failed
gitlab.geo_wikis_checksum_mismatch_count,gauge,,,,Number of wikis that checksum mismatch on secondary,-1,gitlab,db wikis checksum mismatch
gitlab.geo_repositories_checked_count,gauge,,,,Number of repositories that have been checked via git fsck,0,gitlab,db repos checked
gitlab.geo_repositories_checked_failed_count,gauge,,,,Number of repositories that have a failure from git fsck,-1,gitlab,db repos checked failed
gitlab.geo_repositories_retrying_verification_count,gauge,,,,Number of repositories verification failures that Geo is actively trying to correct on secondary,0,gitlab,db repos retry
gitlab.geo_wikis_retrying_verification_count,gauge,,,,Number of wikis verification failures that Geo is actively trying to correct on secondary,0,gitlab,db wikis retry
gitlab.db_load_balancing_hosts,gauge,,host,,Current number of load balancing hosts,0,gitlab,db load balancing
gitlab.unicorn_active_connections,gauge,,connection,,The number of active Unicorn connections (workers),0,gitlab,unicorn active conn
gitlab.unicorn_queued_connections,gauge,,connection,,The number of queued Unicorn connections,0,gitlab,unicorn queued conn
gitlab.unicorn_workers,gauge,,worker,,The number of Unicorn workers,0,gitlab,unicorn workers
gitlab.puma_workers,gauge,,worker,,Total number of puma workers,0,gitlab,puma workers
gitlab.puma_running_workers,gauge,,worker,,Number of booted puma workers,0,gitlab,puma running workers
gitlab.puma_stale_workers,gauge,,worker,,Number of old puma workers,0,gitlab,puma old workers
gitlab.puma_running,gauge,,thread,,Number of running puma threads,0,gitlab,puma run
gitlab.puma_queued_connections,gauge,,connection,,Number of connections in that puma worker’s “todo” set waiting for a worker thread,0,gitlab,puma queued conn
gitlab.puma_active_connections,gauge,,thread,,Number of puma threads processing a request,0,gitlab,puma active conn
gitlab.puma_pool_capacity,gauge,,request,,Number of requests the puma worker is capable of taking right now,0,gitlab,puma pool cap
gitlab.puma_max_threads,gauge,,thread,,Maximum number of puma worker threads,0,gitlab,puma worker max
gitlab.puma_idle_threads,gauge,,thread,,Number of spawned puma threads which are not processing a request,0,gitlab,puma idle threads
gitlab.puma_killer_terminations_total,gauge,,worker,,Number of workers terminated by PumaWorkerKiller,0,gitlab,puma terminations


LEGACY_METRICS_MAP = {}
gitlab.go_gc_duration_seconds,gauge,,request,second,A summary of the GC invocation durations,0,gitlab,gc duration
gitlab.go_gc_duration_seconds_sum,gauge,,request,second,Sum of the GC invocation durations,0,gitlab,sum gc duration
gitlab.go_gc_duration_seconds_count,gauge,,request,second,Count of the GC invocation durations,0,gitlab,count gc duration
gitlab.go_goroutines,gauge,,request,second,Number of goroutines that currently exist,0,gitlab,goroutines
gitlab.go_memstats_alloc_bytes,gauge,,byte,,Number of bytes allocated and still in use,0,gitlab,bytes allocated in use
gitlab.go_memstats_alloc_bytes_total,count,,byte,,Total number of bytes allocated,0,gitlab,bytes allocated
gitlab.go_memstats_buck_hash_sys_bytes,gauge,,byte,,Number of bytes used by the profiling bucket hash table,0,gitlab,bytes profiling bucket
gitlab.go_memstats_frees_total,count,,request,,Total number of frees,0,gitlab,number of frees
gitlab.go_memstats_gc_cpu_fraction,gauge,,request,second,The fraction of this program's available CPU time used by the GC since the program started,0,gitlab,GC cpu fraction
gitlab.go_memstats_gc_sys_bytes,gauge,,byte,,Number of bytes used for garbage collection system metadata,0,gitlab,bytes garbage collection
gitlab.go_memstats_heap_alloc_bytes,gauge,,byte,,Number of heap bytes allocated and still in use,0,gitlab,heap bytes allocated and in use
gitlab.go_memstats_heap_idle_bytes,gauge,,byte,,Number of heap bytes waiting to be used,0,gitlab,heap bytes unused
gitlab.go_memstats_heap_inuse_bytes,gauge,,byte,,Number of heap bytes that are in use,0,gitlab,heap bytes in use
gitlab.go_memstats_heap_objects,gauge,,request,,Number of allocated objects,0,gitlab,allocated objects
gitlab.go_memstats_heap_released_bytes_total,count,,byte,,Total number of heap bytes released to OS,0,gitlab,heap bytes released
gitlab.go_memstats_heap_sys_bytes,gauge,,byte,,Number of heap bytes obtained from system,0,gitlab,heap bytes obtained
gitlab.go_memstats_last_gc_time_seconds,gauge,,request,,Number of seconds since 1970 of last garbage collection,0,gitlab,epoch since last gc
gitlab.go_memstats_lookups_total,count,,request,,Total number of pointer lookups,0,gitlab,pointer lookups
gitlab.go_memstats_mallocs_total,count,,request,,Total number of mallocs,0,gitlab,number of mallocs
gitlab.go_memstats_mcache_inuse_bytes,gauge,,byte,,Number of bytes in use by mcache structures,0,gitlab,mcache bytes used
gitlab.go_memstats_mcache_sys_bytes,gauge,,byte,,Number of bytes used for mcache structures obtained from system,0,gitlab,mcache bytes from sys
gitlab.go_memstats_mspan_inuse_bytes,gauge,,byte,,Number of bytes in use by mspan structures,0,gitlab,mspan bytes used
gitlab.go_memstats_mspan_sys_bytes,gauge,,byte,,Number of bytes used for mspan structures obtained from system,0,gitlab,mspan bytes from sys
gitlab.go_memstats_next_gc_bytes,gauge,,byte,,Number of heap bytes when next garbage collection will take place,0,gitlab,heap bytes next gc
gitlab.go_memstats_other_sys_bytes,gauge,,byte,,Number of bytes used for other system allocations,0,gitlab,other bytes used
gitlab.go_memstats_stack_inuse_bytes,gauge,,byte,,Number of bytes in use by the stack allocator,0,gitlab,bytes stack allocator
gitlab.go_memstats_stack_sys_bytes,gauge,,byte,,Number of bytes obtained from system for stack allocator,0,gitlab,bytes stack allocator from sys
gitlab.go_memstats_sys_bytes,gauge,,byte,,Number of bytes obtained by system. Sum of all system allocations,0,gitlab,sum system allocations
gitlab.go_threads,gauge,,request,second,Number of OS threads create,0,gitlab,go threads
gitlab.http_request_duration_microseconds,gauge,,request,second,The HTTP request latencies in microseconds,0,gitlab,HTTP req latencies
gitlab.http_request_size_bytes,gauge,,byte,,The HTTP request sizes in bytes,0,gitlab,HTTP req sizes
gitlab.http_requests_total,count,,request,second,Total number of HTTP requests made,0,gitlab,total HTTP reqs
gitlab.http_response_size_bytes,gauge,,byte,,The HTTP response sizes in bytes,0,gitlab,HTTP resp sizes
gitlab.process_cpu_seconds_total,count,,request,second,Total user and system CPU time spent in seconds,0,gitlab,user and system cpu time
gitlab.process_max_fds,gauge,,request,,Maximum number of open file descriptors,0,gitlab,max fds
gitlab.process_open_fds,gauge,,request,,Number of open file descriptors,0,gitlab,open fds
gitlab.process_resident_memory_bytes,gauge,,byte,,Resident memory size in bytes,0,gitlab,rss bytes
gitlab.process_start_time_seconds,gauge,,request,second,Start time of the process since unix epoch in seconds,0,gitlab,epoch time since start
gitlab.process_virtual_memory_bytes,gauge,,byte,,Virtual memory size in bytes,0,gitlab,virtual memory bytes
gitlab.prometheus_build_info,gauge,,request,second,A metric with a constant '1' value labeled by version revision branch and goversion from which prometheus was built,0,gitlab,build info
gitlab.prometheus_config_last_reload_success_timestamp_seconds,gauge,,request,second,Timestamp of the last successful configuration reload,0,gitlab,Timestamp successful config reload
gitlab.prometheus_config_last_reload_successful,gauge,,request,second,Whether the last configuration reload attempt was successful,0,gitlab,flag successful config reload
gitlab.prometheus_engine_queries,gauge,,request,second,The current number of queries being executed or waiting,0,gitlab,current queries
gitlab.prometheus_engine_queries_concurrent_max,gauge,,request,second,The max number of concurrent queries,0,gitlab,max concurrent queries
gitlab.prometheus_engine_query_duration_seconds,gauge,,request,second,Query timing,0,gitlab,query timing
gitlab.prometheus_evaluator_duration_seconds,gauge,,request,second,The duration of rule group evaluations,0,gitlab,duration evaluator
gitlab.prometheus_evaluator_iterations_missed_total,count,,request,second,The total number of rule group evaluations missed due to slow rule group evaluation,0,gitlab,total evaluations missed
gitlab.prometheus_evaluator_iterations_skipped_total,count,,request,second,The total number of rule group evaluations skipped due to throttled metric storage,0,gitlab,total evaluations skipped
gitlab.prometheus_evaluator_iterations_total,count,,request,second,The total number of scheduled rule group evaluations whether executed missed or skipped,0,gitlab,total evaluations scheduled
gitlab.prometheus_local_storage_checkpoint_duration_seconds,gauge,,request,second,The duration in seconds taken for checkpointing open chunks and chunks yet to be persisted,0,gitlab,duration checkpointing open chunks
gitlab.prometheus_local_storage_checkpoint_last_duration_seconds,gauge,,request,second,The duration in seconds it took to last checkpoint open chunks and chunks yet to be persisted,0,gitlab,duration last checkpoint open chunks
gitlab.prometheus_local_storage_checkpoint_last_size_bytes,gauge,,byte,,The size of the last checkpoint of open chunks and chunks yet to be persisted,0,gitlab,size last checkpoint open chunks
gitlab.prometheus_local_storage_checkpoint_series_chunks_written,gauge,,request,second,The number of chunk written per series while checkpointing open chunks and chunks yet to be persisted,0,gitlab,checkpoint series chunks written
gitlab.prometheus_local_storage_checkpointing,gauge,,request,second,1 if the storage is checkpointing and 0 otherwise,0,gitlab,storage checkpointing flag
gitlab.prometheus_local_storage_chunk_ops_total,count,,request,second,The total number of chunk operations by their type,0,gitlab,chunk ops by type
gitlab.prometheus_local_storage_chunks_to_persist,count,,request,second,The current number of chunks waiting for persistence,0,gitlab,chunks to be persisted
gitlab.prometheus_local_storage_fingerprint_mappings_total,count,,request,second,The total number of fingerprints being mapped to avoid collisions,0,gitlab,fingerprints mapped
gitlab.prometheus_local_storage_inconsistencies_total,count,,request,second,A counter incremented each time an inconsistency in the local storage is detected. If this is greater zero then restart the server as soon as possible,0,gitlab,total storage inconsistencies
gitlab.prometheus_local_storage_indexing_batch_duration_seconds,gauge,,request,second,Quantiles for batch indexing duration in seconds,0,gitlab,batch indexing duration quantiles
gitlab.prometheus_local_storage_indexing_batch_sizes,gauge,,request,second,Quantiles for indexing batch sizes (number of metrics per batch),0,gitlab,indexing batch sizes quantiles
gitlab.prometheus_local_storage_indexing_queue_capacity,gauge,,request,second,The capacity of the indexing queue,0,gitlab,indexing queue capacity
gitlab.prometheus_local_storage_indexing_queue_length,gauge,,request,second,The number of metrics waiting to be indexed,0,gitlab,metrics queued for indexing
gitlab.prometheus_local_storage_ingested_samples_total,count,,request,second,The total number of samples ingested,0,gitlab,samples ingested
gitlab.prometheus_local_storage_maintain_series_duration_seconds,gauge,,request,second,The duration in seconds it took to perform maintenance on a series,0,gitlab,series maintenance duration
gitlab.prometheus_local_storage_memory_chunkdescs,gauge,,request,second,The current number of chunk descriptors in memory,0,gitlab,chunk descriptors in memory
gitlab.prometheus_local_storage_memory_chunks,gauge,,request,second,The current number of chunks in memory. The number does not include cloned chunks (i.e. chunks without a descriptor),0,gitlab,chunks in memory
gitlab.prometheus_local_storage_memory_dirty_series,gauge,,request,second,The current number of series that would require a disk seek during crash recovery,0,gitlab,memory dirty series
gitlab.prometheus_local_storage_memory_series,gauge,,request,second,The current number of series in memory,0,gitlab,series in memory
gitlab.prometheus_local_storage_non_existent_series_matches_total,count,,request,second,How often a non-existent series was referred to during label matching or chunk preloading. This is an indication of outdated label indexes,0,gitlab,total non-existent series matches
gitlab.prometheus_local_storage_open_head_chunks,gauge,,request,second,The current number of open head chunks,0,gitlab,open head chunks
gitlab.prometheus_local_storage_out_of_order_samples_total,count,,request,second,The total number of samples that were discarded because their timestamps were at or before the last received sample for a series,0,gitlab,samples out of order
gitlab.prometheus_local_storage_persist_errors_total,count,,request,second,The total number of errors while writing to the persistence layer,0,gitlab,persistence write errors
gitlab.prometheus_local_storage_persistence_urgency_score,gauge,,request,second,A score of urgency to persist chunks. 0 is least urgent and 1 most,0,gitlab,chunk persistence urgency score
gitlab.prometheus_local_storage_queued_chunks_to_persist_total,count,,request,second,The total number of chunks queued for persistence,0,gitlab,chunks queued for persistence
gitlab.prometheus_local_storage_rushed_mode,gauge,,request,second,1 if the storage is in rushed mode and 0 otherwise,0,gitlab,flag storage in rushed mode
gitlab.prometheus_local_storage_series_chunks_persisted,gauge,,request,second,The number of chunks persisted per series,0,gitlab,chunks persisted per series
gitlab.prometheus_local_storage_series_ops_total,count,,request,second,The total number of series operations by their type,0,gitlab,series ops by type
gitlab.prometheus_local_storage_started_dirty,gauge,,request,second,Whether the local storage was found to be dirty (and crash recovery occurred) during Prometheus startup,0,gitlab,local storage started dirty
gitlab.prometheus_local_storage_target_heap_size_bytes,gauge,,byte,,The configured target heap size in bytes,0,gitlab,target heap size
gitlab.prometheus_notifications_alertmanagers_discovered,gauge,,request,second,The number of alertmanagers discovered and active,0,gitlab,alertmanagers active
gitlab.prometheus_notifications_dropped_total,count,,request,second,Total number of alerts dropped due to errors when sending to Alertmanager,0,gitlab,alerts dropped
gitlab.prometheus_notifications_queue_capacity,gauge,,request,second,The capacity of the alert notifications queue,0,gitlab,alert notifications capacity
gitlab.prometheus_notifications_queue_length,gauge,,request,second,The number of alert notifications in the queue,0,gitlab,alert notifications queued
gitlab.prometheus_rule_evaluation_failures_total,gauge,,request,second,The total number of rule evaluation failures,0,gitlab,evaluation failures
gitlab.prometheus_sd_azure_refresh_duration_seconds,gauge,,request,second,The duration of a Azure-SD refresh in seconds,0,gitlab,Azure-SD refresh duration
gitlab.prometheus_sd_azure_refresh_failures_total,count,,request,second,Number of Azure-SD refresh failures,0,gitlab,Azure-SD refresh failures
gitlab.prometheus_sd_consul_rpc_duration_seconds,gauge,,request,second,The duration of a Consul RPC call in seconds,0,gitlab,Consul RPC call duration
gitlab.prometheus_sd_consul_rpc_failures_total,count,,request,second,The number of Consul RPC call failures,0,gitlab,Consul RPC lookup failures
gitlab.prometheus_sd_dns_lookup_failures_total,count,,request,second,The number of DNS-SD lookup failures,0,gitlab,DNS-SD lookup failures
gitlab.prometheus_sd_dns_lookups_total,count,,request,second,The number of DNS-SD lookups,0,gitlab,DNS-SD lookups
gitlab.prometheus_sd_ec2_refresh_duration_seconds,gauge,,request,second,The duration of a EC2-SD refresh in seconds,0,gitlab,EC2-SD refresh duration
gitlab.prometheus_sd_ec2_refresh_failures_total,count,,request,second,The number of EC2-SD scrape failures,0,gitlab,EC2-SD scrape failures
gitlab.prometheus_sd_file_read_errors_total,count,,request,second,The number of File-SD read errors,0,gitlab,File-SD read errors
gitlab.prometheus_sd_file_scan_duration_seconds,gauge,,request,second,The duration of the File-SD scan in seconds,0,gitlab,File-SD scan duration
gitlab.prometheus_sd_gce_refresh_duration,gauge,,request,second,The duration of a GCE-SD refresh in seconds,0,gitlab,GCE-SD refresh duration
gitlab.prometheus_sd_gce_refresh_failures_total,count,,request,second,The number of GCE-SD refresh failures,0,gitlab,GCE-SD refresh failures
gitlab.prometheus_sd_kubernetes_events_total,count,,request,second,The number of Kubernetes events handled,0,gitlab,K8s events handled
gitlab.prometheus_sd_marathon_refresh_duration_seconds,gauge,,request,second,The duration of a Marathon-SD refresh in seconds,0,gitlab,Marathon-SD refresh duration
gitlab.prometheus_sd_marathon_refresh_failures_total,count,,request,second,The number of Marathon-SD refresh failures,0,gitlab,Marathon-SD refresh failures
gitlab.prometheus_sd_openstack_refresh_duration_seconds,gauge,,request,second,The duration of an OpenStack-SD refresh in seconds,0,gitlab,OpenStack-SD refresh duration
gitlab.prometheus_sd_openstack_refresh_failures_total,count,,request,second,The number of OpenStack-SD scrape failures,0,gitlab,OpenStack-SD scrape failures
gitlab.prometheus_sd_triton_refresh_duration_seconds,gauge,,request,second,The duration of a Triton-SD refresh in seconds,0,gitlab,Triton-SD refresh duration
gitlab.prometheus_sd_triton_refresh_failures_total,count,,request,second,The number of Triton-SD scrape failures,0,gitlab,Triton-SD scrape failures
gitlab.prometheus_target_interval_length_seconds,gauge,,request,second,Actual intervals between scrapes,0,gitlab,interval between scrapes
gitlab.prometheus_target_scrape_pool_sync_total,count,,request,second,Total number of syncs that were executed on a scrape pool,0,gitlab,total syncs on scrape pool
gitlab.prometheus_target_scrapes_exceeded_sample_limit_total,gauge,,request,second,Total number of scrapes that hit the sample limit and were rejected,0,gitlab,total scrapes rejected
gitlab.prometheus_target_skipped_scrapes_total,count,,request,second,Total number of scrapes that were skipped because the metric storage was throttled,0,gitlab,total scrapes skipped
gitlab.prometheus_target_sync_length_seconds,gauge,,request,second,Actual interval to sync the scrape pool,0,gitlab,scrape pool sync interval
gitlab.prometheus_treecache_watcher_goroutines,gauge,,request,second,The current number of watcher goroutines,0,gitlab,watcher goroutines
gitlab.prometheus_treecache_zookeeper_failures_total,count,,request,second,The total number of ZooKeeper failures,0,gitlab,total Zookeeper failures
