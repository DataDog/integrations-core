METRICS_MAP = {
	"gitlab_banzai_cached_render_real_duration_seconds_count": "banzai_cached_render_real_duration_seconds_count",
	"gitlab_banzai_cached_render_real_duration_seconds_sum": "banzai_cached_render_real_duration_seconds_sum"


}

gitlab.banzai_cached_render_real_duration_seconds_sum,gauge,,second,,Sum of duration of rendering Markdown into HTML when cached output exists,0,gitlab,cached render duration sum
gitlab.banzai_cacheless_render_real_duration_seconds_count,,count,,second,,Count of duration of rendering Markdown into HTML when cached output does not exist,0,gitlab,cachless render duration count
gitlab.banzai_cacheless_render_real_duration_seconds,gauge,,second,,Sum of duration of rendering Markdown into HTML when cached output does not exist,0,gitlab,cachless render duration sum
gitlab.cache_misses_total,count,,second,,Cache read miss count,0,gitlab,cache read miss
gitlab.cache_operation_duration_seconds_count,,count,,second,,Count of cache access time,0,gitlab,cache access time count
gitlab.cache_operation_duration_seconds_sum,,gauge,,second,,Sum of cache access time,0,gitlab,cache access time sum
gitlab.cache_operations_total,count,,,,Count of cache operations by controller/action,0,gitlab,cache operations total
gitlab.database_transaction_seconds_count,count,,seconds,,Count of cache operations by controller/action,0,gitlab,cache operations total count
gitlab.database_transaction_seconds_sum,gauge,,seconds,,Sum of cache operations by controller/action,0,gitlab,cache operations total sum
gitlab.method_call_duration_seconds_count,count,,seconds,,Count of method calls real duration,0,gitlab,method call count
gitlab.method_call_duration_seconds_sum,gauge,,seconds,,Sum of method calls real duration,0,gitlab,method call sum
gitlab.page_out_of_bounds,count,,,,Counter for the PageLimiter pagination limit being hit,-1,gitlab,page out of bounds
gitlab.rails_queue_duration_seconds_count,count,,seconds,,Counter for latency between GitLab Workhorse forwarding a request to Rails,0,gitlab,rails queue duration count
gitlab.rails_queue_duration_seconds_sum,gauge,,seconds,,Sum of latency between GitLab Workhorse forwarding a request to Rails,0,gitlab,rails queue duration sum
gitlab.sql_duration_seconds_count,count,,seconds,,Total SQL execution time, excluding SCHEMA operations and BEGIN / COMMIT,0,gitlab,sql duration count
gitlab.sql_duration_seconds_sum,gauge,,seconds,,Sum of SQL execution time, excluding SCHEMA operations and BEGIN / COMMIT,0,gitlab,sql duration sum
gitlab.transaction_allocated_memory_bytes_count,count,,bytes,,Count of allocated memory for all transactions (gitlab_transaction_* metrics),0,gitlab,transaction allocated memory count
gitlab.transaction_allocated_memory_bytes_sum,gauge,,bytes,,Sum of allocated memory for all transactions (gitlab_transaction_* metrics),0,gitlab,transaction allocated memory sum
gitlab.transaction_cache_count_total,count,,,,Counter for total Rails cache calls (aggregate),0,gitlab,transaction cache calls
gitlab.transaction_cache_duration_total,count,,seconds,,Counter for total time (seconds) spent in Rails cache calls (aggregate),0,gitlab,transaction cache duration
gitlab.transaction_cache_read_hit_count_total,count,,,,Counter for cache hits for Rails cache calls,0,gitlab,transaction cache hits
gitlab.transaction_cache_read_miss_count_total,count,,,,Counter for cache misses for Rails cache calls,0,gitlab,transaction cache misses
gitlab.transaction_duration_seconds_count,count,,,,Count of Duration for all transactions (gitlab_transaction_* metrics),0,gitlab,transaction duration count
gitlab.transaction_duration_seconds_sum,gauge,,,,Sum of Duration for all transactions (gitlab_transaction_* metrics),0,gitlab,transaction duration sum
gitlab.transaction_event_build_found_total,count,,,,Counter for build found for API /jobs/request,0,gitlab,build found count
gitlab.transaction_event_build_invalid_total,count,,,,Counter for build invalid due to concurrency conflict for API /jobs/request,-1,gitlab,build invalid count
gitlab.transaction_event_build_not_found_cached_total,count,,,,Counter for build invalid due to concurrency conflict for API /jobs/request,-1,gitlab,build not found cached
gitlab.transaction_event_build_not_found_total,count,,,,Counter for build not found for API /jobs/request,-1,gitlab,build not found total
gitlab.transaction_event_change_default_branch_total,count,,,,Counter when default branch is changed for any repository,0,gitlab,change default branch
gitlab.transaction_event_create_repository_total,count,,,,Counter when any repository is created,0,gitlab,create repository total
gitlab.transaction_event_etag_caching_cache_hit_total,count,,,,Counter for etag cache hit.,0,gitlab,etag cache hit
gitlab.transaction_event_etag_caching_header_missing_total,count,,,,Counter for etag cache miss - header missing,0,gitlab,etag cache hit missing header
gitlab.transaction_event_etag_caching_key_not_found_total,count,,,,Counter for etag cache miss - key not found,0,gitlab,etag cache hit key
gitlab.transaction_event_etag_caching_middleware_used_total,count,,,,Counter for etag middleware accessed,0,gitlab,etag middleware
gitlab.transaction_event_etag_caching_resource_changed_total,count,,,,Counter for etag cache miss - resource changed,0,gitlab,etag cache miss
gitlab.transaction_event_fork_repository_total,count,,,,Counter for repository forks (RepositoryForkWorker). Only incremented when source repository exists,0,gitlab,repo fork
gitlab.transaction_event_import_repository_total,count,,,,Counter for repository imports (RepositoryImportWorker),0,gitlab,repo imports
gitlab.transaction_event_push_branch_total,count,,,,Counter for all branch pushes,0,gitlab,branch pushes
gitlab.transaction_event_push_commit_total,count,,,,Counter for commits,0,gitlab,commits pushes
gitlab.transaction_event_push_tag_total,count,,,,Counter for tag pushes,0,gitlab,tags pushes
gitlab.transaction_event_rails_exception_total,count,,,,Counter for number of rails exceptions,-1,gitlab,rails exceptions
gitlab.transaction_event_receive_email_total,count,,,,Counter for received emails,0,gitlab,recieved emails
gitlab.transaction_event_remote_mirrors_failed_total,count,,,,Counter for failed remote mirrors,0,gitlab,remote mirrors failed
gitlab.transaction_event_remote_mirrors_finished_total,count,,,,Counter for finished remote mirrors,0,gitlab,remote mirrors finished
gitlab.transaction_event_remote_mirrors_running_total,count,,,,Counter for running remote mirrors,0,gitlab,remote mirrors running
gitlab.transaction_event_remove_branch_total,count,,,,Counter when a branch is removed for any repository,0,gitlab,branches removed
gitlab.transaction_event_remove_repository_total,count,,,,Counter when a repository is removed,0,gitlab,repos removed
gitlab.transaction_event_remove_tag_total,count,,,,Counter when a tag is remove for any repository,0,gitlab,tags removed
gitlab.transaction_event_sidekiq_exception_total,count,,,,Counter of Sidekiq exceptions,-1,gitlab,sidekiq exceptions
gitlab.transaction_event_stuck_import_jobs_total,count,,,,Count of stuck import jobs,-1,gitlab,stuck import jobs
gitlab.transaction_event_update_build_total,count,,,,Counter for update build for API /jobs/request/:id,0,gitlab,update build
gitlab.transaction_new_redis_connections_total,count,,,,Counter for new Redis connections,0,gitlab,new redis connections
gitlab.transaction_queue_duration_total,count,,,,Duration jobs were enqueued before processing,0,gitlab,jobs enqueued processing
gitlab.transaction_rails_queue_duration_total,count,,,,Measures latency between GitLab Workhorse forwarding a request to Rails,0,gitlab,rails queue duration
gitlab.transaction_view_duration_total,count,,,,Duration for views,0,gitlab,view duration
gitlab.transaction_view_duration_total_sum,count,,,,Sum of duration for views,0,gitlab,view duration sum
gitlab.view_rendering_duration_seconds_count,count,,,,Count of duration for views (histogram),0,gitlab,rendering duration count
gitlab.view_rendering_duration_seconds_sum,count,,,,Sum of duration for views (histogram),0,gitlab,rendering duration sum
gitlab.http_requests_total.sum,count,,,,Rack request count,0,gitlab,rack request count
gitlab.http_request_duration_seconds_sum,count,,,,Sum of HTTP response time from rack middleware,0,gitlab,http request dur sum
gitlab.http_request_duration_seconds_count,count,,,,Count of HTTP response time from rack middleware,0,gitlab,http request dur sum

gitlab.pipelines_created_total,count,,,,Counter of pipelines created,0,gitlab,pipelines created total
gitlab.rack_uncaught_errors_total,count,,,,Rack connections handling uncaught errors count,-1,gitlab,rack uncaught errors
gitlab.user_session_logins_total,count,,,,Counter of how many users have logged in,0,gitlab,user logins
gitlab.upload_file_does_not_exist,count,,,,Number of times an upload record could not find its file,0,no upload file
gitlab.failed_login_captcha_total,gauge,,,,Counter of failed CAPTCHA attempts during login,-1,failed captchas
gitlab.successful_login_captcha_total,gauge,,,,Counter of successful CAPTCHA attempts during login,0,successful captchas
gitlab.auto_devops_pipelines_completed_total,count,,,,"Counter of completed Auto DevOps pipelines, labeled by status",0,completed auto pipelines
gitlab.sidekiq_jobs_cpu_seconds_count,count,,second,,Count of seconds of cpu time to run Sidekiq job,0,cpu sidekiq count
gitlab.sidekiq_jobs_cpu_seconds_sum,count,,second,,Sum of seconds of cpu time to run Sidekiq job,0,sidekiq cpu sum
gitlab.sidekiq_jobs_completion_seconds_count,count,,second,,Count of seconds to complete Sidekiq job,0,sidekiq completion count
gitlab.sidekiq_jobs_completion_seconds_sum,count,,second,,Sum of seconds to complete Sidekiq job,0,sidekiq completion sum
gitlab.sidekiq_jobs_queue_duration_seconds_count,count,,second,,Count of duration in seconds that a Sidekiq job was queued before being executed,0,sidekiq queue count
gitlab.sidekiq_jobs_queue_duration_seconds_sum,count,,second,,Sum of duration in seconds that a Sidekiq job was queued before being executed,0,sidekiq queue sum
gitlab.sidekiq_jobs_failed_total,count,,job,,Sidekiq jobs failed,-1,sidekiq jobs failed
gitlab.sidekiq_jobs_retried_total,count,,job,,Sidekiq jobs retired,0,sidekiq jobs retried
gitlab.sidekiq_running_jobs,gauge,,job,,Number of Sidekiq jobs running,0,sidekiq jobs running
gitlab.sidekiq_concurrency,gauge,,job,,Maximum number of Sidekiq jobs,0,sidekiq jobs max
gitlab.ruby_gc_duration_seconds,gauge,,second,,Time spent by Ruby in GC,0,ruby gc dur
gitlab.ruby_file_descriptors,gauge,,,,File descriptors per process,0,ruby file descriptors
gitlab.ruby_memory_bytes,gauge,,byte,,Memory usage by process,0,ruby memory process
gitlab.ruby_sampler_duration_seconds,count,,second,,Time spent collecting stats,0,ruby sampler dur
gitlab.ruby_process_cpu_seconds_total,gauge,,second,,Total amount of CPU time per process,0,ruby cpu process
gitlab.ruby_process_max_fds,gauge,,,,Maximum number of open file descriptors per process,0,ruby max fds
gitlab.ruby_process_resident_memory_bytes,gauge,,byte,,Memory usage by process,0,ruby memory
gitlab.ruby_process_start_time_seconds,gauge,,second,,UNIX timestamp of process start time,0,ruby start

##TODO: ALL ruby_gc_stat_...

gitlab.ruby_gc_stat_count,gauge,,,,Number of ruby garbage collectors,0,ruby gc count
gitlab.ruby_gc_stat_heap_allocated_pages,gauge,,,,Number of currently allocated heap pages,0,ruby gc allocated pages
gitlab.ruby_gc_stat_heap_sorted_length,gauge,,,,Length of the heap in memory,0,ruby gc heap length
gitlab.ruby_gc_stat_heap_allocatable_pages,gauge,,,,Number malloced pages that can be used,0,ruby gc heap allocatable
gitlab.ruby_gc_stat_heap_available_slots,gauge,,,,Number of slots in heap pages,0,ruby gc heap slots
gitlab.ruby_gc_stat_heap_live_slots,gauge,,,,Number of live slots in heap,0,ruby gc heap live slots
gitlab.ruby_gc_stat_heap_free_slots,gauge,,,,Number of empty slots in heap,0,ruby gc heap live slots
gitlab.ruby_gc_stat_heap_final_slots,gauge,,,,Number of slots in heap with finalizers,0,ruby gc heap final slots

