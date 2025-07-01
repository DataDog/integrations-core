# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# E501: line too long (XXX > 120 characters)
# flake8: noqa: E501
# Source for metric names: https://github.com/temporalio/temporal/blob/master/common/metrics/metric_defs.go
METRIC_MAP = {
    # General
    'service_requests': 'service.requests',
    'service_pending_requests': 'service.pending_requests',
    'service_errors': 'service.errors',
    'service_error_with_type': 'service.error_with_type',
    'service_errors_critical': 'service.errors.critical',
    'service_errors_resource_exhausted': 'service.errors.resource_exhausted',
    'service_latency': 'service.latency',
    'service_latency_nouserlatency': 'service.latency.nouserlatency',
    'service_latency_userlatency': 'service.latency.userlatency',
    'action': 'action',
    'certificates_expired': 'certificates.expired',
    'certificates_expiring': 'certificates.expiring',
    'service_authorization_latency': 'service.authorization_latency',
    'event_blob_size': 'event.blob_size',
    'namespace_cache_prepare_callbacks_latency': 'namespace_cache.prepare_callbacks_latency',
    'namespace_cache_callbacks_latency': 'namespace_cache.callbacks_latency',
    'lock_requests': 'lock.requests',
    'lock_failures': 'lock.failures',
    'lock_latency': 'lock.latency',
    'client_requests': 'client.requests',
    'client_errors': 'client.errors',
    'client_latency': 'client.latency',
    'client_redirection_requests': 'client.redirection.requests',
    'client_redirection_errors': 'client.redirection.errors',
    'client_redirection_latency': 'client.redirection.latency',
    'state_transition_count': 'state_transition',
    'history_size': 'history.size',
    'history_count': 'history',
    'search_attributes_size': 'search_attributes_size',
    'memo_size': 'memo_size',
    'wf_too_many_pending_child_workflows': 'wf_too_many_pending.child_workflows',
    'wf_too_many_pending_activities': 'wf_too_many_pending.activities',
    'wf_too_many_pending_cancel_requests': 'wf_too_many_pending.cancel_requests',
    'wf_too_many_pending_external_workflow_signals': 'wf_too_many_pending.external_workflow_signals',
    # Frontend
    'add_search_attributes_workflow_success': 'add_search_attributes.workflow_success',
    'add_search_attributes_workflow_failure': {
        'name': 'add_search_attributes.workflow_failure',
        'type': 'native_dynamic',
    },
    'delete_namespace_workflow_success': 'delete_namespace.workflow_success',
    'delete_namespace_workflow_failure': 'delete_namespace.workflow_failure',
    'version_check_success': 'version_check.success',
    'version_check_failed': 'version_check.failed',
    'version_check_request_failed': 'version_check.request_failed',
    'version_check_latency': 'version_check.latency',
    # History
    'cache_requests': 'cache.requests',
    'cache_errors': 'cache.errors',
    'cache_latency': 'cache.latency',
    'cache_miss': 'cache.miss',
    'history_event_notification_queueing_latency': 'history.event_notification.queueing_latency',
    'history_event_notification_fanout_latency': 'history.event_notification.fanout_latency',
    'history_event_notification_inflight_message_gauge': 'history.event_notification.inflight_message',
    'history_event_notification_fail_delivery_count': 'history.event_notification.fail_delivery',
    'archival_task_invalid_uri': 'archival.task_invalid_uri',
    'archiver_client_sent_signal': 'archiver.client.sent_signal',
    'archiver_client_send_signal_error': 'archiver.client.send_signal_error',
    'archiver_client_history_request': 'archiver.client.history.request',
    'archiver_client_history_inline_archive_attempt': 'archiver.client.history.inline_archive.attempt',
    'archiver_client_history_inline_archive_failure': 'archiver.client.history.inline_archive.failure',
    'archiver_client_visibility_request': 'archiver.client.visibility.request',
    'archiver_client_visibility_inline_archive_attempt': 'archiver.client.visibility.inline_archive_attempt',
    'archiver_client_visibility_inline_archive_failure': 'archiver.client.visibility.inline_archive_failure',
    'archiver_archive_latency': 'archiver.archive.latency',
    'archiver_archive_target_latency': 'archiver.archive.target_latency',
    'shard_closed_count': 'shard_closed',
    'sharditem_created_count': 'sharditem.created',
    'sharditem_removed_count': 'sharditem.removed',
    'sharditem_acquisition_latency': 'sharditem.acquisition_latency',
    'shardinfo_replication_pending_task': 'shardinfo.replication.pending_task',
    'shardinfo_transfer_active_pending_task': 'shardinfo.transfer.active.pending_task',
    'shardinfo_transfer_standby_pending_task': 'shardinfo.transfer.standby.pending_task',
    'shardinfo_timer_active_pending_task': 'shardinfo.timer.active.pending_task',
    'shardinfo_timer_standby_pending_task': 'shardinfo.timer.standby.pending_task',
    'shardinfo_visibility_pending_task': 'shardinfo.visibility.pending_task',
    'shardinfo_replication_lag': 'shardinfo.replication.lag',
    'shardinfo_transfer_lag': 'shardinfo.transfer.lag',
    'shardinfo_timer_lag': 'shardinfo.timer.lag',
    'shardinfo_visibility_lag': 'shardinfo.visibility.lag',
    'shardinfo_immediate_queue_lag': 'shardinfo.immediate_queue.lag',
    'shardinfo_scheduled_queue_lag': 'shardinfo.scheduled_queue.lag',
    'syncshard_remote_count': 'syncshard.remote',
    'syncshard_remote_failed': 'syncshard.remote.failed',
    'task_requests': 'task.requests',
    'task_latency_load': 'task.latency.load',
    'task_latency_schedule': 'task.latency.schedule',
    'task_latency_processing': 'task.latency.processing',
    'task_latency_user': 'task.latency.user',
    'task_latency': 'task.latency',
    'task_latency_queue': 'task.latency.queue',
    'task_attempt': 'task.attempt',
    'task_errors': 'task.errors',
    'task_errors_discarded': 'task.errors.discarded',
    'task_skipped': 'task.skipped',
    'task_errors_version_mismatch': 'task.errors.version_mismatch',
    'task_dependency_task_not_completed': 'task.dependency_task_not_completed',
    'task_errors_standby_retry_counter': 'task.errors.standby_retry_counter',
    'task_errors_workflow_busy': 'task.errors.workflow_busy',
    'task_errors_not_active_counter': 'task.errors.not_active_counter',
    'task_errors_limit_exceeded_counter': 'task.errors.limit_exceeded_counter',
    'task_errors_namespace_handover': 'task.errors.namespace_handover',
    'task_errors_throttled': 'task.errors.throttled',
    'task_errors_corruption': 'task.errors.corruption',
    'task_schedule_to_start_latency': 'task.schedule_to_start_latency',
    'transfer_task_missing_event_counter': 'transfer_task.missing_event_counter',
    'task_batch_complete_counter': 'task.batch_complete_counter',
    'task_rescheduler_pending_tasks': 'task_rescheduler.pending_tasks',
    'pending_tasks': 'pending_tasks',
    'task_scheduler_throttled': 'task_scheduler.throttled',
    'queue_latency_schedule': 'queue.latency_schedule',
    'queue_reader_count': 'queue.reader',
    'queue_slice_count': 'queue.slice',
    'queue_actions': 'queue.actions',
    'activity_end_to_end_latency': 'activity.end_to_end_latency',
    'ack_level_update': 'ack_level.update',
    'ack_level_update_failed': 'ack_level.update.failed',
    'schedule_activity_command': 'schedule_activity_command',
    'complete_workflow_command': 'complete_workflow_command',
    'fail_workflow_command': 'fail_workflow_command',
    'cancel_workflow_command': 'cancel_workflow_command',
    'start_timer_command': 'start_timer_command',
    'cancel_activity_command': 'cancel_activity_command',
    'cancel_timer_command': 'cancel_timer_command',
    'record_marker_command': 'record_marker_command',
    'cancel_external_workflow_command': 'cancel_external_workflow_command',
    'continue_as_new_command': 'continue_as_new_command',
    'signal_external_workflow_command': 'signal_external_workflow_command',
    'upsert_workflow_search_attributes_command': 'upsert_workflow_search_attributes_command',
    'modify_workflow_properties_command': 'modify_workflow_properties_command',
    'child_workflow_command': 'child_workflow_command',
    'accept_workflow_update_message': 'accept_workflow_update_message',
    'complete_workflow_update_message': 'complete_workflow_update_message',
    'reject_workflow_update_message': 'reject_workflow_update_message',
    'activity_eager_execution': 'activity.eager_execution',
    'workflow_eager_execution': 'workflow.eager_execution',
    'workflow_eager_execution_denied': 'workflow.eager_execution.denied',
    'empty_completion_commands': 'empty_completion_commands',
    'multiple_completion_commands': 'multiple_completion_commands',
    'failed_workflow_tasks': 'failed_workflow_tasks',
    'workflow_task_attempt': 'workflow.task.attempt',
    'stale_mutable_state': 'stale_mutable_state',
    'auto_reset_points_exceed_limit': 'auto_reset_points.exceed_limit',
    'auto_reset_point_corruption': 'auto_reset_point.corruption',
    'concurrency_update_failure': 'concurrency_update_failure',
    'service_errors_shard_ownership_lost': 'service.errors.shard_ownership_lost',
    'service_errors_task_already_started': 'service.errors.task_already_started',
    'heartbeat_timeout': 'heartbeat.timeout',
    'schedule_to_start_timeout': 'schedule_to_start.timeout',
    'start_to_close_timeout': 'start_to_close.timeout',
    'schedule_to_close_timeout': 'schedule_to_close.timeout',
    'new_timer_notifications': 'new_timer_notifications',
    'acquire_shards_count': 'acquire_shards',
    'acquire_shards_latency': 'acquire_shards.latency',
    'membership_changed_count': 'membership_changed',
    'numshards_gauge': 'numshards',
    'get_engine_for_shard_errors': 'get_engine_for_shard.errors',
    'get_engine_for_shard_latency': 'get_engine_for_shard.latency',
    'remove_engine_for_shard_latency': 'remove_engine_for_shard.latency',
    'complete_workflow_task_sticky_enabled_count': 'complete_workflow_task_sticky.enabled',
    'complete_workflow_task_sticky_disabled_count': 'complete_workflow_task_sticky.disabled',
    'workflow_task_heartbeat_timeout_count': 'workflow.task.heartbeat_timeout',
    'empty_replication_events': 'empty_replication_events',
    'duplicate_replication_events': 'duplicate_replication_events',
    'stale_replication_events': 'stale_replication_events',
    'replication_events_size': 'replication_events_size',
    'buffer_replication_tasks': 'buffer_replication_tasks',
    'unbuffer_replication_tasks': 'unbuffer_replication_tasks',
    'history_conflicts': 'history.conflicts',
    'complete_task_fail_count': 'complete_task_fail',
    'acquire_lock_failed': 'acquire_lock_failed',
    'workflow_context_cleared': 'workflow.context_cleared',
    'mutable_state_size': 'mutable_state.size',
    'execution_info_size': 'execution_info.size',
    'execution_state_size': 'execution_state.size',
    'activity_info_size': 'activity_info.size',
    'timer_info_size': 'timer_info.size',
    'child_info_size': 'child_info.size',
    'request_cancel_info_size': 'request_cancel_info.size',
    'signal_info_size': 'signal_info.size',
    'buffered_events_size': 'buffered_events.size',
    'activity_info_count': 'activity_info',
    'timer_info_count': 'timer_info',
    'child_info_count': 'child_info',
    'signal_info_count': 'signal_info',
    'request_cancel_info_count': 'request_cancel_info',
    'buffered_events_count': 'buffered_events',
    'task_count': 'task',
    'workflow_retry_backoff_timer': 'workflow.retry_backoff.timer',
    'workflow_cron_backoff_timer': 'workflow.cron_backoff.timer',
    'workflow_cleanup_delete': 'workflow.cleanup.delete',
    'workflow_cleanup_archive': 'workflow.cleanup.archive',
    'workflow_cleanup_nop': 'workflow.cleanup.nop',
    'workflow_cleanup_delete_history_inline': 'workflow.cleanup.delete_history_inline',
    'workflow_success': 'workflow.success',
    'workflow_cancel': 'workflow.cancel',
    'workflow_failed': 'workflow.failed',
    'workflow_timeout': 'workflow.timeout',
    'workflow_terminate': 'workflow.terminate',
    'workflow_continued_as_new': 'workflow.continued_as_new',
    'last_retrieved_message_id': 'last_retrieved_message_id',
    'last_processed_message_id': 'last_processed_message_id',
    'replication_tasks_applied': 'replication.tasks.applied',
    'replication_tasks_failed': 'replication.tasks.failed',
    'replication_tasks_lag': 'replication.tasks.lag',
    'replication_latency': 'replication.latency',
    'replication_tasks_fetched': 'replication.tasks.fetched',
    'replication_tasks_returned': 'replication.tasks.returned',
    'replication_tasks_applied_latency': 'replication.tasks.applied_latency',
    'replication_dlq_enqueue_failed': 'replication.dlq.enqueue_failed',
    'replication_dlq_max_level': 'replication.dlq.max_level',
    'replication_dlq_ack_level': 'replication.dlq.ack_level',
    'get_replication_messages_for_shard': 'get_replication_messages_for_shard',
    'get_dlq_replication_messages': 'get_dlq_replication_messages',
    'event_reapply_skipped_count': 'event.reapply_skipped',
    'direct_query_dispatch_latency': 'direct_query_dispatch.latency',
    'direct_query_dispatch_sticky_latency': 'direct_query_dispatch.sticky.latency',
    'direct_query_dispatch_non_sticky_latency': 'direct_query_dispatch.non_sticky.latency',
    'direct_query_dispatch_sticky_success': 'direct_query_dispatch.sticky.success',
    'direct_query_dispatch_non_sticky_success': 'direct_query_dispatch.non_sticky.success',
    'direct_query_dispatch_clear_stickiness_latency': 'direct_query_dispatch.clear_stickiness.latency',
    'direct_query_dispatch_clear_stickiness_success': 'direct_query_dispatch.clear_stickiness.success',
    'direct_query_dispatch_timeout_before_non_sticky': 'direct_query_dispatch.timeout_before_non_sticky',
    'workflow_task_query_latency': 'workflow.task.query_latency',
    'consistent_query_timeout': 'consistent_query_timeout',
    'query_before_first_workflow_task': 'query_before_first_workflow_task',
    'query_buffer_exceeded': 'query_buffer_exceeded',
    'query_registry_invalid_state': 'query_registry_invalid_state',
    'worker_not_supports_consistent_query': 'worker_not_supports_consistent_query',
    'workflow_task_timeout_overrides': 'workflow.task.timeout_overrides',
    'workflow_run_timeout_overrides': 'workflow.run_timeout_overrides',
    'replication_task_cleanup_count': 'replication.task_cleanup',
    'replication_task_cleanup_failed': 'replication.task_cleanup.failed',
    'mutable_state_checksum_mismatch': 'mutable_state_checksum.mismatch',
    'mutable_state_checksum_invalidated': 'mutable_state_checksum.invalidated',
    'cluster_metadata_lock_latency': 'cluster_metadata.lock_latency',
    'cluster_metadata_callback_lock_latency': 'cluster_metadata.callback.lock_latency',
    'shard_controller_lock_latency': 'shard_controller.lock_latency',
    'shard_lock_latency': 'shard.lock_latency',
    'namespace_registry_lock_latency': 'namespace_registry.lock_latency',
    'closed_workflow_buffer_event_counter': 'closed_workflow_buffer_event_counter',
    'inordered_buffered_events': 'inordered_buffered_events',
    # Matching
    'forwarded': 'forwarded',
    'invalid_task_queue_name': 'invalid_task_queue_name',
    'syncmatch_latency': 'syncmatch.latency',
    'asyncmatch_latency': 'asyncmatch.latency',
    'poll_success': 'poll.success',
    'poll_timeouts': 'poll.timeouts',
    'poll_success_sync': 'poll.success_sync',
    'lease_requests': 'lease.requests',
    'lease_failures': 'lease.failures',
    'condition_failed_errors': 'condition_failed_errors',
    'respond_query_failed': 'respond_query_failed',
    'sync_throttle_count': 'sync_throttle',
    'buffer_throttle_count': 'buffer_throttle',
    'tasks_expired': 'tasks_expired',
    'forwarded_per_tl': 'forwarded_per_tl',
    'forward_task_calls': 'forward_task.calls',
    'forward_task_errors': 'forward_task.errors',
    'forward_query_calls': 'forward_query.calls',
    'forward_query_errors': 'forward_query.errors',
    'forward_poll_calls': 'forward_poll.calls',
    'forward_poll_errors': 'forward_poll.errors',
    'forward_task_latency': 'forward_task.latency',
    'forward_query_latency': 'forward_query.latency',
    'forward_poll_latency': 'forward_poll.latency',
    'local_to_local_matches': 'local_to_local.matches',
    'local_to_remote_matches': 'local_to_remote.matches',
    'remote_to_local_matches': 'remote_to_local.matches',
    'remote_to_remote_matches': 'remote_to_remote.matches',
    'loaded_task_queue_count': 'loaded_task_queue_count',
    'task_queue_started': 'task_queue.started',
    'task_queue_stopped': 'task_queue.stopped',
    'task_write_throttle_count': 'task.write.throttle',
    'task_write_latency': 'task.write.latency',
    'task_lag_per_tl': 'task.lag_per_tl',
    'no_poller_tasks': 'no_poller_tasks',
    # Worker
    'executor_done': 'executor.done',
    'executor_err': 'executor.err',
    'executor_deferred': 'executor.deferred',
    'executor_dropped': 'executor.dropped',
    'started': 'started',
    'stopped': 'stopped',
    'scan_duration': 'scan_duration',
    'task_processed': 'task.processed',
    'task_deleted': 'task.deleted',
    'taskqueue_processed': 'taskqueue.processed',
    'taskqueue_deleted': 'taskqueue.deleted',
    'taskqueue_outstanding': 'taskqueue.outstanding',
    'history_archiver_archive_non_retryable_error': 'history.archiver.archive.non_retryable_error',
    'history_archiver_archive_transient_error': 'history.archiver.archive.transient_error',
    'history_archiver_archive_success': 'history.archiver.archive.success',
    'history_archiver_history_mutated': 'history.archiver.history_mutated',
    'history_archiver_total_upload_size': 'history.archiver.total_upload_size',
    'history_archiver_history_size': 'history.archiver.history_size',
    'history_archiver_duplicate_archivals': 'history.archiver.duplicate_archivals',
    'history_archiver_blob_exists': 'history.archiver.blob_exists',
    'history_archiver_blob_size': 'history.archiver.blob_size',
    'history_archiver_running_deterministic_construction_check': 'history.archiver.running_deterministic_construction_check',
    'history_archiver_deterministic_construction_check_failed': 'history.archiver.deterministic_construction_check_failed',
    'history_archiver_running_blob_integrity_check': 'history.archiver.running_blob_integrity_check',
    'history_archiver_blob_integrity_check_failed': 'history.archiver.blob_integrity_check_failed',
    'history_workflow_execution_cache_latency': 'history.workflow_execution_cache_latency',
    'visibility_archiver_archive_non_retryable_error': 'visibility.archiver.archive.non_retryable_error',
    'visibility_archiver_archive_transient_error': 'visibility.archiver.archive.transient_error',
    'visibility_archiver_archive_success': 'visibility.archiver.archive.success',
    'scavenger_success': 'scavenger.success',
    'scavenger_errors': 'scavenger.errors',
    'scavenger_skips': 'scavenger.skips',
    'executions_outstanding': 'executions_outstanding',
    'archiver_non_retryable_error': 'archiver.non_retryable_error',
    'archiver_started': 'archiver.started',
    'archiver_stopped': 'archiver.stopped',
    'archiver_coroutine_started': 'archiver.coroutine.started',
    'archiver_coroutine_stopped': 'archiver.coroutine.stopped',
    'archiver_handle_history_request_latency': 'archiver.handle_history.request.latency',
    'archiver_handle_visibility_request_latency': 'archiver.handle_visibility.request.latency',
    'archiver_upload_with_retries_latency': 'archiver.upload.with_retries.latency',
    'archiver_delete_with_retries_latency': 'archiver.delete.with_retries.latency',
    'archiver_upload_failed_all_retries': 'archiver.upload.failed_all_retries',
    'archiver_upload_success': 'archiver.upload.success',
    'archiver_delete_failed_all_retries': 'archiver.delete.failed_all_retries',
    'archiver_delete_success': 'archiver.delete.success',
    'archiver_handle_visibility_failed_all_retries': 'archiver.handle_visibility.failed_all_retries',
    'archiver_handle_visibility_success': 'archiver.handle_visibility.success',
    'archiver_backlog_size': 'archiver.backlog.size',
    'archiver_pump_timeout': 'archiver.pump.timeout',
    'archiver_pump_signal_threshold': 'archiver.pump.signal_threshold',
    'archiver_pump_timeout_without_signals': 'archiver.pump.timeout_without_signals',
    'archiver_pump_signal_channel_closed': 'archiver.pump.signal_channel_closed',
    'archiver_workflow_started': 'archiver.workflow.started',
    'archiver_num_pumped_requests': 'archiver.num_pumped_requests',
    'archiver_num_handled_requests': 'archiver.num_handled_requests',
    'archiver_pumped_not_equal_handled': 'archiver.pumped_not_equal_handled',
    'archiver_handle_all_requests_latency': 'archiver.handle_all_requests_latency',
    'archiver_workflow_stopping': 'archiver.workflow.stopping',
    'scavenger_validation_requests': 'scavenger.validation.requests',
    'scavenger_validation_failures': 'scavenger.validation.failures',
    'scavenger_validation_skips': 'scavenger.validation.skips',
    'add_search_attributes_failures': 'add_search_attributes.failures',
    'delete_namespace_success': 'delete_namespace.success',
    'rename_namespace_success': 'rename_namespace.success',
    'delete_executions_success': 'delete_executions.success',
    'delete_namespace_failures': 'delete_namespace.failures',
    'update_namespace_failures': 'update_namespace.failures',
    'rename_namespace_failures': 'rename_namespace.failures',
    'read_namespace_failures': 'read_namespace.failures',
    'list_executions_failures': 'list_executions.failures',
    'count_executions_failures': 'count_executions.failures',
    'delete_execution_failures': 'delete_execution.failures',
    'delete_execution_not_found': 'delete_execution.not_found',
    'rate_limiter_failures': 'rate_limiter.failures',
    'batcher_processor_requests': 'batcher.processor_requests',
    'batcher_processor_errors': 'batcher.processor_errors',
    'batcher_operation_errors': 'batcher.operation_errors',
    'elasticsearch_bulk_processor_requests': 'elasticsearch.bulk_processor.requests',
    'elasticsearch_bulk_processor_queued_requests': 'elasticsearch.bulk_processor.queued_requests',
    'elasticsearch_bulk_processor_errors': 'elasticsearch.bulk_processor.errors',
    'elasticsearch_bulk_processor_corrupted_data': 'elasticsearch.bulk_processor.corrupted_data',
    'elasticsearch_bulk_processor_duplicate_request': 'elasticsearch.bulk_processor.duplicate_request',
    'elasticsearch_bulk_processor_request_latency': 'elasticsearch.bulk_processor.request.latency',
    'elasticsearch_bulk_processor_commit_latency': 'elasticsearch.bulk_processor.commit.latency',
    'elasticsearch_bulk_processor_wait_add_latency': 'elasticsearch.bulk_processor.wait_add.latency',
    'elasticsearch_bulk_processor_wait_start_latency': 'elasticsearch.bulk_processor.wait_start.latency',
    'elasticsearch_bulk_processor_bulk_size': 'elasticsearch.bulk_processor.bulk_size',
    'elasticsearch_document_parse_failures_counter': 'elasticsearch.document.parse_failures_counter',
    'elasticsearch_document_generate_failures_counter': 'elasticsearch.document.generate_failures_counter',
    'catchup_ready_shard_count': 'catchup.ready_shard_count',
    'handover_ready_shard_count': 'handover.ready_shard_count',
    'replicator_messages': 'replicator.messages',
    'replicator_errors': 'replicator.errors',
    'replicator_latency': 'replicator.latency',
    'replicator_dlq_enqueue_fails': 'replicator.dlq_enqueue_fails',
    'namespace_replication_dlq_enqueue_requests': 'namespace_replication.dlq_enqueue_requests',
    'parent_close_policy_processor_requests': 'parent_close_policy_processor.requests',
    'parent_close_policy_processor_errors': 'parent_close_policy_processor.errors',
    'schedule_missed_catchup_window': 'schedule.missed_catchup_window',
    'schedule_rate_limited': 'schedule.rate_limited',
    'schedule_buffer_overruns': 'schedule.buffer_overruns',
    'schedule_action_success': 'schedule.action.success',
    'schedule_action_errors': 'schedule.action.errors',
    'schedule_cancel_workflow_errors': 'schedule.cancel_workflow.errors',
    'schedule_terminate_workflow_errors': 'schedule.terminate_workflow.errors',
    # Replication
    'namespace_replication_task_ack_level': 'namespace_replication.task_ack_level',
    'namespace_dlq_ack_level': 'namespace_dlq.ack_level',
    'namespace_dlq_max_level': 'namespace_dlq.max_level',
    # Persistence
    'persistence_requests': 'persistence.requests',
    'persistence_errors': 'persistence.errors',
    'persistence_error_with_type': 'persistence.error_with_type',
    'persistence_latency': 'persistence.latency',
    'persistence_errors_resource_exhausted': 'persistence.errors.resource_exhausted',
    'visibility_persistence_requests': 'visibility.persistence.requests',
    'visibility_persistence_error_with_type': 'visibility.persistence.error_with_type',
    'visibility_persistence_errors': 'visibility.persistence.errors',
    'visibility_persistence_resource_exhausted': 'visibility.persistence.resource_exhausted',
    'visibility_persistence_latency': 'visibility.persistence.latency',
    'elasticsearch_bulk_processor_retries': 'elasticsearch.bulk_processor_retries',  # added in temporal version v1.19.0
    'namespace_registry_callback_lock_latency': 'namespace_registry.callback_lock_latency',  # added in temporal version v1.19.0
    'persistence_errors_bad_request': 'persistence.errors.bad_request',  # added in temporal version v1.19.0
    'persistence_errors_busy': 'persistence.errors.busy',  # added in temporal version v1.19.0
    'persistence_errors_condition_failed': 'persistence.errors.condition_failed',  # added in temporal version v1.19.0
    'persistence_errors_current_workflow_condition_failed': 'persistence.errors.current_workflow_condition_failed',  # added in temporal version v1.19.0
    'persistence_errors_entity_not_exists': 'persistence.errors.entity_not_exists',  # added in temporal version v1.19.0
    'persistence_errors_namespace_already_exists': 'persistence.errors.namespace_already_exists',  # added in temporal version v1.19.0
    'persistence_errors_shard_exists': 'persistence.errors.shard_exists',  # added in temporal version v1.19.0
    'persistence_errors_shard_ownership_lost': 'persistence.errors.shard_ownership_lost',  # added in temporal version v1.19.0
    'persistence_errors_timeout': 'persistence.errors.timeout',  # added in temporal version v1.19.0
    'persistence_errors_workflow_condition_failed': 'persistence.errors.workflow_condition_failed',  # added in temporal version v1.19.0
    'service_errors_authorize_failed': 'service.errors.authorize_failed',  # added in temporal version v1.19.0
    'service_errors_bad_binary': 'service.errors.bad_binary',  # added in temporal version v1.19.0
    'service_errors_cancellation_already_requested': 'service.errors.cancellation_already_requested',  # added in temporal version v1.19.0
    'service_errors_client_version_not_supported': 'service.errors.client_version_not_supported',  # added in temporal version v1.19.0
    'service_errors_context_cancelled': 'service.errors.context_cancelled',  # added in temporal version v1.19.0
    'service_errors_context_timeout': 'service.errors.context_timeout',  # added in temporal version v1.19.0
    'service_errors_entity_not_found': 'service.errors.entity_not_found',  # added in temporal version v1.19.0
    'service_errors_execution_already_started': 'service.errors.execution_already_started',  # added in temporal version v1.19.0
    'service_errors_incomplete_history': 'service.errors.incomplete_history',  # added in temporal version v1.19.0
    'service_errors_invalid_argument': 'service.errors.invalid_argument',  # added in temporal version v1.19.0
    'service_errors_namespace_already_exists': 'service.errors.namespace_already_exists',  # added in temporal version v1.19.0
    'service_errors_namespace_not_active': 'service.errors.namespace_not_active',  # added in temporal version v1.19.0
    'service_errors_nondeterministic': 'service.errors.nondeterministic',  # added in temporal version v1.19.0
    'service_errors_query_failed': 'service.errors.query_failed',  # added in temporal version v1.19.0
    'service_errors_retry_task': 'service.errors.retry_task',  # added in temporal version v1.19.0
    'service_errors_unauthorized': 'service.errors.unauthorized',  # added in temporal version v1.19.0
    'shardinfo_timer_diff': 'shardinfo.timer_diff',  # added in temporal version v1.19.0
    'shardinfo_timer_failover_in_progress': 'shardinfo.timer_failover_in_progress',  # added in temporal version v1.19.0
    'shardinfo_timer_failover_latency': 'shardinfo.timer_failover_latency',  # added in temporal version v1.19.0
    'shardinfo_transfer_diff': 'shardinfo.transfer.diff',  # added in temporal version v1.19.0
    'shardinfo_transfer_failover_in_progress': 'shardinfo.transfer.failover_in_progress',  # added in temporal version v1.19.0
    'shardinfo_transfer_failover_latency': 'shardinfo.transfer.failover_latency',  # added in temporal version v1.19.0
    'task_throttled_counter': 'task.throttled_counter',  # added in temporal version v1.19.0
    'elasticsearch_bulk_processor_bulk_request_took_latency': 'elasticsearch.bulk_processor.bulk_request_took_latency',  # added in temporal version v1.21.0
    'elasticsearch_custom_order_by_clause_counter': 'elasticsearch.custom_order_by_clause_counter',  # added in temporal version v1.21.0
    'invalid_state_transition_workflow_update_message': 'invalid_state_transition_workflow_update_message',  # added in temporal version v1.21.0
    'persistence_shard_rps': 'persistence.shard_rps',  # added in temporal version v1.21.0
    'protocol_message_command': 'protocol_message_command',  # added in temporal version v1.21.0
    'queue_action_errors': 'queue.action_errors',  # added in temporal version v1.21.0
    'replication_dlq_non_empty': 'replication.dlq_non_empty',  # added in temporal version v1.21.0
    'replication_tasks_recv': 'replication.tasks_recv',  # added in temporal version v1.21.0
    'replication_tasks_recv_backlog': 'replication.tasks_recv_backlog',  # added in temporal version v1.21.0
    'replication_tasks_send': 'replication.tasks_send',  # added in temporal version v1.21.0
    'request_workflow_update_message': 'request_workflow_update_message',  # added in temporal version v1.21.0
    'respond_workflow_update_message': 'respond_workflow_update_message',  # added in temporal version v1.21.0
    'signal_request_id_count': 'signal_request_id_count',  # added in temporal version v1.21.0
    'signal_request_id_size': 'signal_request_id_size',  # added in temporal version v1.21.0
    'total_activity_count': 'total_activity_count',  # added in temporal version v1.21.0
    'total_child_execution_count': 'total_child_execution_count',  # added in temporal version v1.21.0
    'total_request_cancel_external_count': 'total_request_cancel_external_count',  # added in temporal version v1.21.0
    'total_signal_count': 'total_signal_count',  # added in temporal version v1.21.0
    'total_signal_external_count': 'total_signal_external_count',  # added in temporal version v1.21.0
    'total_user_timer_count': 'total_user_timer_count',  # added in temporal version v1.21.0
    'workflow_delayed_start_backoff_timer': 'workflow_delayed_start.backoff_timer',  # added in temporal version v1.21.0
    'encounter_not_found_workflow_count': 'encounter_not_found_workflow_count',  # added in temporal version v1.22.0
    'encounter_pass_retention_workflow_count': 'encounter_pass_retention_workflow_count',  # added in temporal version v1.22.0
    'encounter_zombie_workflow_count': 'encounter_zombie_workflow_count',  # added in temporal version v1.22.0
    'generate_replication_tasks_latency': 'generate_replication_tasks_latency',  # added in temporal version v1.22.0
    'http_service_requests': 'http.service_requests',  # added in temporal version v1.22.0
    'mutable_state_dirty': 'mutable_state_dirty',  # added in temporal version v1.22.0
    'replication_outlier_namespace': 'replication.outlier_namespace',  # added in temporal version v1.22.0
    'replication_tasks_skipped': 'replication.tasks_skipped',  # added in temporal version v1.22.0
    'service_panics': 'service.panics',  # added in temporal version v1.22.0
    'shard_linger_success': 'shard.linger_success',  # added in temporal version v1.22.0
    'shard_linger_timeouts': 'shard.linger_timeouts',  # added in temporal version v1.22.0
    'unknown_build_polls': 'unknown_build.polls',  # added in temporal version v1.22.0
    'unknown_build_tasks': 'unknown_build.tasks',  # added in temporal version v1.22.0
    'verify_describe_mutable_state_latency': 'verify.describe_mutable_state_latency',  # added in temporal version v1.22.0
    'verify_replication_task_failed': 'verify.replication_task.failed',  # added in temporal version v1.22.0
    'verify_replication_task_not_found': 'verify.replication_task.not_found',  # added in temporal version v1.22.0
    'verify_replication_task_success': 'verify.replication_task.success',  # added in temporal version v1.22.0
    'verify_replication_tasks_latency': 'verify.replication_tasks.latency',  # added in temporal version v1.22.0
    'batchable_task_batch_count': 'batchable_task.batch_count',  # added in temporal version v1.23.0
    'cassandra_init_session_latency': 'cassandra.init_session.latency',  # added in temporal version v1.23.0
    'cassandra_session_refresh_failures': 'cassandra.session_refresh.failures',  # added in temporal version v1.23.0
    'command': 'command',  # added in temporal version v1.23.0
    'dd_cluster_metadata_callback_lock_latency': 'dd.cluster_metadata.callback_lock.latency',  # added in temporal version v1.23.0
    'dd_cluster_metadata_lock_latency': 'dd.cluster_metadata_lock_latency',  # added in temporal version v1.23.0
    'dd_namespace_registry_lock_latency': 'dd.namespace_registry_lock_latency',  # added in temporal version v1.23.0
    'dd_shard_controller_lock_latency': 'dd.shard_controller_lock_latency',  # added in temporal version v1.23.0
    'dd_shard_io_semaphore_latency': 'dd.shard_io_semaphore_latency',  # added in temporal version v1.23.0
    'dd_shard_lock_latency': 'dd.shard_lock_latency',  # added in temporal version v1.23.0
    'dlq_writes': 'dlq_writes',  # added in temporal version v1.23.0
    'dynamic_rate_limit_multiplier': 'dynamic_rate_limit_multiplier',  # added in temporal version v1.23.0
    'poll_latency': 'poll_latency',  # added in temporal version v1.23.0
    'replication_stream_panic': 'replication.stream_panic',  # added in temporal version v1.23.0
    'replication_task_transmission_latency': 'replication.task_transmission_latency',  # added in temporal version v1.23.0
    'schedule_action_delay': 'schedule_action_delay',  # added in temporal version v1.23.0
    'semaphore_failures': 'semaphore.failures',  # added in temporal version v1.23.0
    'semaphore_latency': 'semaphore.latency',  # added in temporal version v1.23.0
    'semaphore_requests': 'semaphore.requests',  # added in temporal version v1.23.0
    'task_dispatch_latency': 'task.dispatch_latency',  # added in temporal version v1.23.0
    'task_dlq_failures': 'task.dlq_failures',  # added in temporal version v1.23.0
    'task_dlq_latency': 'task.dlq_latency',  # added in temporal version v1.23.0
    'task_terminal_failures': 'task.terminal_failures',  # added in temporal version v1.23.0
    'cache_entry_age_on_eviction': 'cache_entry.age_on_eviction',  # added in temporal version v1.24.0
    'cache_entry_age_on_get': 'cache_entry.age_on_get',  # added in temporal version v1.24.0
    'cache_pinned_usage': 'cache.pinned_usage',  # added in temporal version v1.24.0
    'cache_size': 'cache.size',  # added in temporal version v1.24.0
    'cache_ttl': 'cache.ttl',  # added in temporal version v1.24.0
    'cache_usage': 'cache.usage',  # added in temporal version v1.24.0
    'gomaxprocs': 'gomaxprocs',  #  added in temporal version v1.24.0
    'host_rps_limit': 'host_rps_limit',  # added in temporal version v1.24.0
    'invalid_task_queue_partition': 'invalid_task_queue_partition',  # added in temporal version v1.24.0
    'loaded_physical_task_queue_count': 'loaded_physical_task_queue_count',  # added in temporal version v1.24.0
    'loaded_task_queue_family_count': 'loaded_task_queue_family_count',  # added in temporal version v1.24.0
    'loaded_task_queue_partition_count': 'loaded_task_queue_partition_count',  # added in temporal version v1.24.0
    'memory_allocated': 'memory.allocated',  # added in temporal version v1.24.0
    'memory_gc_pause_ms': 'memory.gc_pause_ms',  # added in temporal version v1.24.0
    'memory_heap': 'memory.heap',  # added in temporal version v1.24.0
    'memory_heapidle': 'memory.heapidle',  # added in temporal version v1.24.0
    'memory_heapinuse': 'memory.heapinuse',  # added in temporal version v1.24.0
    'memory_num_gc': 'memory.num_gc',  # added in temporal version v1.24.0
    'memory_stack': 'memory.stack',  # added in temporal version v1.24.0
    'namespace_host_rps_limit': 'namespace_host_rps_limit',  # added in temporal version v1.24.0
    'nexus_completion_latency': 'nexus.completion_latency',  # added in temporal version v1.24.0
    'nexus_completion_request_preprocess_errors': 'nexus.completion_request_preprocess_errors',  # added in temporal version v1.24.0
    'nexus_completion_requests': 'nexus.completion_requests',  # added in temporal version v1.24.0
    'nexus_latency': 'nexus.latency',  # added in temporal version v1.24.0
    'nexus_request_preprocess_errors': 'nexus.request_preprocess_errors',  # added in temporal version v1.24.0
    'nexus_requests': 'nexus.requests',  # added in temporal version v1.24.0
    'num_goroutines': 'num_goroutines',  # added in temporal version v1.24.0
    'persisted_mutable_state_size': 'persisted_mutable_state_size',  # added in temporal version v1.24.0
    'reachability_exit_point_count': 'reachability_exit_point_count',  # added in temporal version v1.24.0
    'replication_service_error': 'replication.service_error',  # added in temporal version v1.24.0
    'replication_stream_error': 'replication.stream_error',  # added in temporal version v1.24.0
    'respond_nexus_failed': 'respond_nexus_failed',  #  added in temporal version v1.24.0
    'restarts': 'restarts',  # added in temporal version v1.24.0
    'task_errors_internal': 'task.errors.internal',  # added in temporal version v1.24.0
    'tasks_per_shardinfo_update': 'tasks.per_shardinfo_update',  # added in temporal version v1.24.0
    'time_between_shardinfo_update': 'time_between_shardinfo_update',  # added in temporal version v1.24.0
    'utf8_validation_errors': 'utf8_validation_errors',  # added in temporal version v1.24.0
    'workflow_update_aborted': 'workflow_update.aborted',  # added in temporal version v1.24.0
    'workflow_update_client_timeout': 'workflow_update.client_timeout',  # added in temporal version v1.24.0
    'workflow_update_normal_workflow_task': 'workflow_update.normal_workflow_task',  # added in temporal version v1.24.0
    'workflow_update_registry_size': 'workflow_update.registry_size',  # added in temporal version v1.24.0
    'workflow_update_request_rate_limited': 'workflow_update.request_rate_limited',  # added in temporal version v1.24.0
    'workflow_update_request_too_many': 'workflow_update.request_too_many',  # added in temporal version v1.24.0
    'workflow_update_sent_to_worker': 'workflow_update.sent_to_worker',  # added in temporal version v1.24.0
    'workflow_update_sent_to_worker_again': 'workflow_update.sent_to_worker_again',  # added in temporal version v1.24.0
    'workflow_update_server_timeout': 'workflow_update.server_timeout',  # added in temporal version v1.24.0
    'workflow_update_speculative_workflow_task': 'workflow_update.speculative_workflow_task',  # added in temporal version v1.24.0
    'workflow_update_wait_stage_accepted': 'workflow_update.wait_stage_accepted',  # added in temporal version v1.24.0
    'workflow_update_wait_stage_completed': 'workflow_update.wait_stage_completed',  # added in temporal version v1.24.0
    'approximate_backlog_age_seconds': 'approximate_backlog_age_seconds',  # added in temporal version v1.25.0
    'approximate_backlog_count': 'approximate_backlog_count',  # added in temporal version v1.25.0
    'circuit_breaker_executable_blocked': 'circuit_breaker.executable_blocked',  # added in temporal version v1.25.0
    'dlq_message_count': 'dlq.message_count',  # added in temporal version v1.25.0
    'dynamic_worker_pool_scheduler_active_workers': 'dynamic_worker_pool_scheduler.active_workers',  # added in temporal version v1.25.0
    'dynamic_worker_pool_scheduler_buffer_size': 'dynamic_worker_pool_scheduler.buffer_size',  # added in temporal version v1.25.0
    'dynamic_worker_pool_scheduler_dequeued_tasks': 'dynamic_worker_pool_scheduler.dequeued_tasks',  # added in temporal version v1.25.0
    'dynamic_worker_pool_scheduler_enqueued_tasks': 'dynamic_worker_pool_scheduler.enqueued_tasks',  # added in temporal version v1.25.0
    'dynamic_worker_pool_scheduler_rejected_tasks': 'dynamic_worker_pool_scheduler.rejected_tasks',  # added in temporal version v1.25.0
    'finalizer_items_completed': 'finalizer.items_completed',  # added in temporal version v1.25.0
    'finalizer_items_unfinished': 'finalizer.items_unfinished',  # added in temporal version v1.25.0
    'finalizer_latency': 'finalizer.latency',  # added in temporal version v1.25.0
    'history_workflow_execution_cache_lock_hold_duration': 'history_workflow_execution_cache.lock_hold_duration',  # added in temporal version v1.25.0
    'out_of_order_buffered_events': 'out_of_order_buffered_events',  # added in temporal version v1.25.0
    'persistence_session_refresh_attempts': 'persistence.session_refresh_attempts',  # added in temporal version v1.25.0
    'persistence_session_refresh_failures': 'persistence.session_refresh_failures',  # added in temporal version v1.25.0
    'rate_limited_task_runnable_wait_time': 'rate_limited_task.runnable_wait_time',  # added in temporal version v1.25.0
    'read_namespace_errors': 'read_namespace.errors',  # added in temporal version v1.25.0
    'replication_stream_stuck': 'replication.stream_stuck',  # added in temporal version v1.25.0
    'schedule_action_attempt': 'schedule_action.attempt',  # added in temporal version v1.25.0
    'speculative_workflow_task_commits': 'speculative_workflow_task.commits',  # added in temporal version v1.25.0
    'speculative_workflow_task_rollbacks': 'speculative_workflow_task.rollbacks',  # added in temporal version v1.25.0
    'state_machine_timer_processing_failures': 'state_machine_timer.processing_failures',  # added in temporal version v1.25.0
    'state_machine_timer_skips': 'state_machine_timer.skips',  # added in temporal version v1.25.0
    'workflow_backoff_timer': 'workflow_backoff_timer',  # added in temporal version v1.25.0
    'force_loaded_task_queue_partition_unnecessarily_count': 'force_loaded_task_queue_partition_unnecessarily_count',  # added in temporal version v1.26.0
    'force_loaded_task_queue_partitions_count': 'force_loaded_task_queue_partitions_count',  # added in temporal version v1.26.0
    'signal_with_start_skip_delay_count': 'signal_with_start_skip_delay_count',  # added in temporal version v1.26.0
    'delete_executions_failure': 'delete_executions.failure',  # added in temporal version v1.27.0
    'delete_executions_not_found': 'delete_executions.not_found',  # added in temporal version v1.27.0
    'memory_num_gc_last': 'memory.num_gc_last',  # added in temporal version v1.27.0
    'memory_pause_total_ns_last': 'memory.pause_total_ns_last',  # added in temporal version v1.27.0
    'non_retryable_tasks': 'non_retryable_tasks',  # added in temporal version v1.27.0
    'reclaim_resources_delete_executions_failure': 'reclaim_resources.delete_executions.failure',  # added in temporal version v1.27.0
    'reclaim_resources_delete_executions_success': 'reclaim_resources.delete_executions.success',  # added in temporal version v1.27.0
    'reclaim_resources_namespace_delete_failure': 'reclaim_resources.namespace_delete.failure',  # added in temporal version v1.27.0
    'reclaim_resources_namespace_delete_success': 'reclaim_resources.namespace_delete.success',  # added in temporal version v1.27.0
    'replication_duplicated_task': 'replication.duplicated_task',  # added in temporal version v1.27.0
    'workflow_update_continue_as_new_suggestions': 'workflow_update.continue_as_new_suggestions',  # added in temporal version v1.27.0
    'workflow_update_registry_size_limited': 'workflow_update.registry_size_limited',  # added in temporal version v1.27.0
    'chasm_total_size': 'chasm.total_size',  # added in temporal version v1.28.0
    'dd_current_suspected_deadlocks': 'dd.current_suspected_deadlocks',  # added in temporal version v1.28.0
    'dd_suspected_deadlocks': 'dd.suspected_deadlocks',  # added in temporal version v1.28.0
    'handover_wait_latency': 'handover.wait_latency',  # added in temporal version v1.28.0
    'host_health': 'host.health',  # added in temporal version v1.28.0
    'memory_frees': 'memory.frees',  # added in temporal version v1.28.0
    'memory_heap_objects': 'memory.heap_objects',  # added in temporal version v1.28.0
    'memory_mallocs': 'memory.mallocs',  # added in temporal version v1.28.0
    'operation': 'operation',  # added in temporal version v1.28.0
    'paused_activities': 'paused_activities',  # added in temporal version v1.28.0
    'replication_task_generation_latency': 'replication.task_generation_latency',  # added in temporal version v1.28.0
    'replication_task_load_latency': 'replication.task_load_latency',  # added in temporal version v1.28.0
    'replication_task_load_size': 'replication.task_load_size',  # added in temporal version v1.28.0
    'replication_task_processing_latency': 'replication.task_processing_latency',  # added in temporal version v1.28.0
    'replication_task_send_attempt': 'replication.task_send_attempt',  # added in temporal version v1.28.0
    'replication_task_send_backlog': 'replication.task_send_backlog',  # added in temporal version v1.28.0
    'replication_task_send_error': 'replication.task_send_error',  # added in temporal version v1.28.0
    'replication_task_send_latency': 'replication.task_send_latency',  # added in temporal version v1.28.0
    'replication_tasks_back_fill': 'replication.tasks_back_fill',  # added in temporal version v1.28.0
    'replication_tasks_back_fill_latency': 'replication.tasks_back_fill_latency',  # added in temporal version v1.28.0
    'schedule_action_dropped': 'schedule_action.dropped',  # added in temporal version v1.28.0
    'start_deployment_transition_count': 'start_deployment.transition_count',  # added in temporal version v1.28.0
    'start_workflow_request_deduped': 'start_workflow_request_deduped',  #  added in temporal version v1.28.0
    'task_rewrites': 'task_rewrites',  # added in temporal version v1.28.0
    'worker_deployment_created': 'worker_deployment_created',  # added in temporal version v1.28.0
    'worker_deployment_version_created': 'worker_deployment_version_created',  # added in temporal version v1.28.0
    'worker_deployment_version_created_managed_by_controller': 'worker_deployment_version_created_managed_by_controller',  # added in temporal version v1.28.0
    'worker_deployment_version_visibility_query_count': 'worker_deployment_version_visibility_query_count',  # added in temporal version v1.28.0
    'worker_deployment_versioning_override_count': 'worker_deployment_versioning_override_count',  # added in temporal version v1.28.0
    'workflow_query_failure_count': 'workflow_query.failure_count',  # added in temporal version v1.28.0
    'workflow_query_success_count': 'workflow_query.success_count',  # added in temporal version v1.28.0
    'workflow_query_timeout_count': 'workflow_query.timeout_count',  #  added in temporal version v1.28.0
    'workflow_reset_count': 'workflow_reset_count',  # added in temporal version v1.28.0
    'workflow_tasks_completed': 'workflow_tasks.completed',  # added in temporal version v1.28.0
}
