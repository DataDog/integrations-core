# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
# ruff: noqa: E501

# Common JMX Exporter metrics (shared across all components)
JMX_EXPORTER_METRICS = {
    'jmx_config_reload_failure_created': 'jmx_config_reload_failure_created',
    'jmx_config_reload_failure_total': 'jmx_config_reload_failure_total',
    'jmx_config_reload_success_created': 'jmx_config_reload_success_created',
    'jmx_config_reload_success_total': 'jmx_config_reload_success_total',
    'jmx_exporter_build_info': 'jmx_exporter_build_info',
    'jmx_scrape_cached_beans': 'jmx_scrape_cached_beans',
    'jmx_scrape_duration_seconds': 'jmx_scrape_duration_seconds',
    'jmx_scrape_error': 'jmx_scrape_error',
}

# Common JVM metrics (shared across all components)
JVM_METRICS = {
    'jvm_buffer_pool_capacity_bytes': 'jvm_buffer_pool_capacity_bytes',
    'jvm_buffer_pool_used_buffers': 'jvm_buffer_pool_used_buffers',
    'jvm_buffer_pool_used_bytes': 'jvm_buffer_pool_used_bytes',
    'jvm_classes_currently_loaded': 'jvm_classes_currently_loaded',
    'jvm_classes_loaded_total': 'jvm_classes_loaded_total',
    'jvm_classes_unloaded_total': 'jvm_classes_unloaded_total',
    'jvm_gc_collection_seconds': 'jvm_gc_collection_seconds',
    'jvm_info': 'jvm_info',
    'jvm_memory_bytes_committed': 'jvm_memory_bytes_committed',
    'jvm_memory_bytes_init': 'jvm_memory_bytes_init',
    'jvm_memory_bytes_max': 'jvm_memory_bytes_max',
    'jvm_memory_bytes_used': 'jvm_memory_bytes_used',
    'jvm_memory_objects_pending_finalization': 'jvm_memory_objects_pending_finalization',
    'jvm_memory_pool_allocated_bytes_created': 'jvm_memory_pool_allocated_bytes_created',
    'jvm_memory_pool_allocated_bytes_total': 'jvm_memory_pool_allocated_bytes_total',
    'jvm_memory_pool_bytes_committed': 'jvm_memory_pool_bytes_committed',
    'jvm_memory_pool_bytes_init': 'jvm_memory_pool_bytes_init',
    'jvm_memory_pool_bytes_max': 'jvm_memory_pool_bytes_max',
    'jvm_memory_pool_bytes_used': 'jvm_memory_pool_bytes_used',
    'jvm_memory_pool_collection_committed_bytes': 'jvm_memory_pool_collection_committed_bytes',
    'jvm_memory_pool_collection_init_bytes': 'jvm_memory_pool_collection_init_bytes',
    'jvm_memory_pool_collection_max_bytes': 'jvm_memory_pool_collection_max_bytes',
    'jvm_memory_pool_collection_used_bytes': 'jvm_memory_pool_collection_used_bytes',
    'jvm_threads_current': 'jvm_threads_current',
    'jvm_threads_daemon': 'jvm_threads_daemon',
    'jvm_threads_deadlocked': 'jvm_threads_deadlocked',
    'jvm_threads_deadlocked_monitor': 'jvm_threads_deadlocked_monitor',
    'jvm_threads_peak': 'jvm_threads_peak',
    'jvm_threads_started_total': 'jvm_threads_started_total',
    'jvm_threads_state': 'jvm_threads_state',
}

# Common process metrics (shared across all components)
PROCESS_METRICS = {
    'process_cpu_seconds_total': 'process_cpu_seconds_total',
    'process_max_fds': 'process_max_fds',
    'process_open_fds': 'process_open_fds',
    'process_resident_memory_bytes': 'process_resident_memory_bytes',
    'process_start_time_seconds': 'process_start_time_seconds',
    'process_virtual_memory_bytes': 'process_virtual_memory_bytes',
}

# Common metrics shared across all components
COMMON_METRICS = {**JMX_EXPORTER_METRICS, **JVM_METRICS, **PROCESS_METRICS}

# Controller-specific metrics
CONTROLLER_SPECIFIC_METRICS = {
    # Error metrics
    'pinot_controller_InstanceDeleteError_Count': 'pinot_controller_InstanceDeleteError_Count',
    'pinot_controller_InstanceDeleteError_FifteenMinuteRate': 'pinot_controller_InstanceDeleteError_FifteenMinuteRate',
    'pinot_controller_InstanceDeleteError_FiveMinuteRate': 'pinot_controller_InstanceDeleteError_FiveMinuteRate',
    'pinot_controller_InstanceDeleteError_MeanRate': 'pinot_controller_InstanceDeleteError_MeanRate',
    'pinot_controller_InstanceDeleteError_OneMinuteRate': 'pinot_controller_InstanceDeleteError_OneMinuteRate',
    'pinot_controller_InstancePostError_Count': 'pinot_controller_InstancePostError_Count',
    'pinot_controller_InstancePostError_FifteenMinuteRate': 'pinot_controller_InstancePostError_FifteenMinuteRate',
    'pinot_controller_InstancePostError_FiveMinuteRate': 'pinot_controller_InstancePostError_FiveMinuteRate',
    'pinot_controller_InstancePostError_MeanRate': 'pinot_controller_InstancePostError_MeanRate',
    'pinot_controller_InstancePostError_OneMinuteRate': 'pinot_controller_InstancePostError_OneMinuteRate',
    # Leadership metrics
    'pinot_controller_LeaderPartitionCount_Value': 'pinot_controller_LeaderPartitionCount_Value',
    'pinot_controller_LeadershipChangeWithoutCallback_Count': 'pinot_controller_LeadershipChangeWithoutCallback_Count',
    'pinot_controller_LeadershipChangeWithoutCallback_FifteenMinuteRate': 'pinot_controller_LeadershipChangeWithoutCallback_FifteenMinuteRate',
    'pinot_controller_LeadershipChangeWithoutCallback_FiveMinuteRate': 'pinot_controller_LeadershipChangeWithoutCallback_FiveMinuteRate',
    'pinot_controller_LeadershipChangeWithoutCallback_MeanRate': 'pinot_controller_LeadershipChangeWithoutCallback_MeanRate',
    'pinot_controller_LeadershipChangeWithoutCallback_OneMinuteRate': 'pinot_controller_LeadershipChangeWithoutCallback_OneMinuteRate',
    # Realtime table segment metrics
    'pinot_controller_RealtimeTableSegmentAssignmentError_Count': 'pinot_controller_RealtimeTableSegmentAssignmentError_Count',
    'pinot_controller_RealtimeTableSegmentAssignmentError_FifteenMinuteRate': 'pinot_controller_RealtimeTableSegmentAssignmentError_FifteenMinuteRate',
    'pinot_controller_RealtimeTableSegmentAssignmentError_FiveMinuteRate': 'pinot_controller_RealtimeTableSegmentAssignmentError_FiveMinuteRate',
    'pinot_controller_RealtimeTableSegmentAssignmentError_MeanRate': 'pinot_controller_RealtimeTableSegmentAssignmentError_MeanRate',
    'pinot_controller_RealtimeTableSegmentAssignmentError_OneMinuteRate': 'pinot_controller_RealtimeTableSegmentAssignmentError_OneMinuteRate',
    'pinot_controller_RealtimeTableSegmentAssignmentMismatch_Count': 'pinot_controller_RealtimeTableSegmentAssignmentMismatch_Count',
    'pinot_controller_RealtimeTableSegmentAssignmentMismatch_FifteenMinuteRate': 'pinot_controller_RealtimeTableSegmentAssignmentMismatch_FifteenMinuteRate',
    'pinot_controller_RealtimeTableSegmentAssignmentMismatch_FiveMinuteRate': 'pinot_controller_RealtimeTableSegmentAssignmentMismatch_FiveMinuteRate',
    'pinot_controller_RealtimeTableSegmentAssignmentMismatch_MeanRate': 'pinot_controller_RealtimeTableSegmentAssignmentMismatch_MeanRate',
    'pinot_controller_RealtimeTableSegmentAssignmentMismatch_OneMinuteRate': 'pinot_controller_RealtimeTableSegmentAssignmentMismatch_OneMinuteRate',
    # Schema and table errors
    'pinot_controller_SchemaUploadError_Count': 'pinot_controller_SchemaUploadError_Count',
    'pinot_controller_SchemaUploadError_FifteenMinuteRate': 'pinot_controller_SchemaUploadError_FifteenMinuteRate',
    'pinot_controller_SchemaUploadError_FiveMinuteRate': 'pinot_controller_SchemaUploadError_FiveMinuteRate',
    'pinot_controller_SchemaUploadError_MeanRate': 'pinot_controller_SchemaUploadError_MeanRate',
    'pinot_controller_SchemaUploadError_OneMinuteRate': 'pinot_controller_SchemaUploadError_OneMinuteRate',
    'pinot_controller_SegmentUploadError_Count': 'pinot_controller_SegmentUploadError_Count',
    'pinot_controller_SegmentUploadError_FifteenMinuteRate': 'pinot_controller_SegmentUploadError_FifteenMinuteRate',
    'pinot_controller_SegmentUploadError_FiveMinuteRate': 'pinot_controller_SegmentUploadError_FiveMinuteRate',
    'pinot_controller_SegmentUploadError_MeanRate': 'pinot_controller_SegmentUploadError_MeanRate',
    'pinot_controller_SegmentUploadError_OneMinuteRate': 'pinot_controller_SegmentUploadError_OneMinuteRate',
    'pinot_controller_TableAddError_Count': 'pinot_controller_TableAddError_Count',
    'pinot_controller_TableAddError_FifteenMinuteRate': 'pinot_controller_TableAddError_FifteenMinuteRate',
    'pinot_controller_TableAddError_FiveMinuteRate': 'pinot_controller_TableAddError_FiveMinuteRate',
    'pinot_controller_TableAddError_MeanRate': 'pinot_controller_TableAddError_MeanRate',
    'pinot_controller_TableAddError_OneMinuteRate': 'pinot_controller_TableAddError_OneMinuteRate',
    'pinot_controller_TableSchemaUpdateError_Count': 'pinot_controller_TableSchemaUpdateError_Count',
    'pinot_controller_TableSchemaUpdateError_FifteenMinuteRate': 'pinot_controller_TableSchemaUpdateError_FifteenMinuteRate',
    'pinot_controller_TableSchemaUpdateError_FiveMinuteRate': 'pinot_controller_TableSchemaUpdateError_FiveMinuteRate',
    'pinot_controller_TableSchemaUpdateError_MeanRate': 'pinot_controller_TableSchemaUpdateError_MeanRate',
    'pinot_controller_TableSchemaUpdateError_OneMinuteRate': 'pinot_controller_TableSchemaUpdateError_OneMinuteRate',
    # Tenant errors
    'pinot_controller_TableTenantCreateError_Count': 'pinot_controller_TableTenantCreateError_Count',
    'pinot_controller_TableTenantCreateError_FifteenMinuteRate': 'pinot_controller_TableTenantCreateError_FifteenMinuteRate',
    'pinot_controller_TableTenantCreateError_FiveMinuteRate': 'pinot_controller_TableTenantCreateError_FiveMinuteRate',
    'pinot_controller_TableTenantCreateError_MeanRate': 'pinot_controller_TableTenantCreateError_MeanRate',
    'pinot_controller_TableTenantCreateError_OneMinuteRate': 'pinot_controller_TableTenantCreateError_OneMinuteRate',
    'pinot_controller_TableTenantDeleteError_Count': 'pinot_controller_TableTenantDeleteError_Count',
    'pinot_controller_TableTenantDeleteError_FifteenMinuteRate': 'pinot_controller_TableTenantDeleteError_FifteenMinuteRate',
    'pinot_controller_TableTenantDeleteError_FiveMinuteRate': 'pinot_controller_TableTenantDeleteError_FiveMinuteRate',
    'pinot_controller_TableTenantDeleteError_MeanRate': 'pinot_controller_TableTenantDeleteError_MeanRate',
    'pinot_controller_TableTenantDeleteError_OneMinuteRate': 'pinot_controller_TableTenantDeleteError_OneMinuteRate',
    'pinot_controller_TableTenantUpdateError_Count': 'pinot_controller_TableTenantUpdateError_Count',
    'pinot_controller_TableTenantUpdateError_FifteenMinuteRate': 'pinot_controller_TableTenantUpdateError_FifteenMinuteRate',
    'pinot_controller_TableTenantUpdateError_FiveMinuteRate': 'pinot_controller_TableTenantUpdateError_FiveMinuteRate',
    'pinot_controller_TableTenantUpdateError_MeanRate': 'pinot_controller_TableTenantUpdateError_MeanRate',
    'pinot_controller_TableTenantUpdateError_OneMinuteRate': 'pinot_controller_TableTenantUpdateError_OneMinuteRate',
    'pinot_controller_TableUpdateError_Count': 'pinot_controller_TableUpdateError_Count',
    'pinot_controller_TableUpdateError_FifteenMinuteRate': 'pinot_controller_TableUpdateError_FifteenMinuteRate',
    'pinot_controller_TableUpdateError_FiveMinuteRate': 'pinot_controller_TableUpdateError_FiveMinuteRate',
    'pinot_controller_TableUpdateError_MeanRate': 'pinot_controller_TableUpdateError_MeanRate',
    'pinot_controller_TableUpdateError_OneMinuteRate': 'pinot_controller_TableUpdateError_OneMinuteRate',
    # Periodic task metrics
    'pinot_controller_controllerPeriodicTaskRun_Count': 'pinot_controller_controllerPeriodicTaskRun_Count',
    'pinot_controller_controllerPeriodicTaskRun_FifteenMinuteRate': 'pinot_controller_controllerPeriodicTaskRun_FifteenMinuteRate',
    'pinot_controller_controllerPeriodicTaskRun_FiveMinuteRate': 'pinot_controller_controllerPeriodicTaskRun_FiveMinuteRate',
    'pinot_controller_controllerPeriodicTaskRun_MeanRate': 'pinot_controller_controllerPeriodicTaskRun_MeanRate',
    'pinot_controller_controllerPeriodicTaskRun_OneMinuteRate': 'pinot_controller_controllerPeriodicTaskRun_OneMinuteRate',
    # Gauge metrics
    'pinot_controller_disabledTableCount_Value': 'pinot_controller_disabledTableCount_Value',
    'pinot_controller_droppedBrokerInstances_Value': 'pinot_controller_droppedBrokerInstances_Value',
    'pinot_controller_droppedMinionInstances_Value': 'pinot_controller_droppedMinionInstances_Value',
    'pinot_controller_droppedServerInstances_Value': 'pinot_controller_droppedServerInstances_Value',
    'pinot_controller_exists_Value': 'pinot_controller_exists_Value',
    'pinot_controller_failedToCopySchemaCount_Value': 'pinot_controller_failedToCopySchemaCount_Value',
    'pinot_controller_failedToUpdateTableConfigCount_Value': 'pinot_controller_failedToUpdateTableConfigCount_Value',
    'pinot_controller_fileOpLatencyMs_Value': 'pinot_controller_fileOpLatencyMs_Value',
    'pinot_controller_fixedSchemaTableCount_Value': 'pinot_controller_fixedSchemaTableCount_Value',
    # Healthcheck metrics
    'pinot_controller_healthcheckBadCalls_Count': 'pinot_controller_healthcheckBadCalls_Count',
    'pinot_controller_healthcheckBadCalls_FifteenMinuteRate': 'pinot_controller_healthcheckBadCalls_FifteenMinuteRate',
    'pinot_controller_healthcheckBadCalls_FiveMinuteRate': 'pinot_controller_healthcheckBadCalls_FiveMinuteRate',
    'pinot_controller_healthcheckBadCalls_MeanRate': 'pinot_controller_healthcheckBadCalls_MeanRate',
    'pinot_controller_healthcheckBadCalls_OneMinuteRate': 'pinot_controller_healthcheckBadCalls_OneMinuteRate',
    'pinot_controller_healthcheckOkCalls_Count': 'pinot_controller_healthcheckOkCalls_Count',
    'pinot_controller_healthcheckOkCalls_FifteenMinuteRate': 'pinot_controller_healthcheckOkCalls_FifteenMinuteRate',
    'pinot_controller_healthcheckOkCalls_FiveMinuteRate': 'pinot_controller_healthcheckOkCalls_FiveMinuteRate',
    'pinot_controller_healthcheckOkCalls_MeanRate': 'pinot_controller_healthcheckOkCalls_MeanRate',
    'pinot_controller_healthcheckOkCalls_OneMinuteRate': 'pinot_controller_healthcheckOkCalls_OneMinuteRate',
    # Helix/Zookeeper metrics
    'pinot_controller_helix_ZookeeperReconnects_Count': 'pinot_controller_helix_ZookeeperReconnects_Count',
    'pinot_controller_helix_ZookeeperReconnects_FifteenMinuteRate': 'pinot_controller_helix_ZookeeperReconnects_FifteenMinuteRate',
    'pinot_controller_helix_ZookeeperReconnects_FiveMinuteRate': 'pinot_controller_helix_ZookeeperReconnects_FiveMinuteRate',
    'pinot_controller_helix_ZookeeperReconnects_MeanRate': 'pinot_controller_helix_ZookeeperReconnects_MeanRate',
    'pinot_controller_helix_ZookeeperReconnects_OneMinuteRate': 'pinot_controller_helix_ZookeeperReconnects_OneMinuteRate',
    'pinot_controller_helix_connected_Value': 'pinot_controller_helix_connected_Value',
    'pinot_controller_helix_leader_Value': 'pinot_controller_helix_leader_Value',
    # Other controller metrics
    'pinot_controller_misconfiguredSchemaTableCount_Value': 'pinot_controller_misconfiguredSchemaTableCount_Value',
    'pinot_controller_numMinionSubtasksError_Value': 'pinot_controller_numMinionSubtasksError_Value',
    'pinot_controller_numMinionSubtasksRunning_Value': 'pinot_controller_numMinionSubtasksRunning_Value',
    'pinot_controller_numMinionSubtasksWaiting_Value': 'pinot_controller_numMinionSubtasksWaiting_Value',
    'pinot_controller_numMinionTasksInProgress_Value': 'pinot_controller_numMinionTasksInProgress_Value',
    'pinot_controller_numberSegmentUploadTimeoutExceeded_Count': 'pinot_controller_numberSegmentUploadTimeoutExceeded_Count',
    'pinot_controller_numberSegmentUploadTimeoutExceeded_FifteenMinuteRate': 'pinot_controller_numberSegmentUploadTimeoutExceeded_FifteenMinuteRate',
    'pinot_controller_numberSegmentUploadTimeoutExceeded_FiveMinuteRate': 'pinot_controller_numberSegmentUploadTimeoutExceeded_FiveMinuteRate',
    'pinot_controller_numberSegmentUploadTimeoutExceeded_MeanRate': 'pinot_controller_numberSegmentUploadTimeoutExceeded_MeanRate',
    'pinot_controller_numberSegmentUploadTimeoutExceeded_OneMinuteRate': 'pinot_controller_numberSegmentUploadTimeoutExceeded_OneMinuteRate',
    'pinot_controller_numberTimesScheduleTasksCalled_Count': 'pinot_controller_numberTimesScheduleTasksCalled_Count',
    'pinot_controller_numberTimesScheduleTasksCalled_FifteenMinuteRate': 'pinot_controller_numberTimesScheduleTasksCalled_FifteenMinuteRate',
    'pinot_controller_numberTimesScheduleTasksCalled_FiveMinuteRate': 'pinot_controller_numberTimesScheduleTasksCalled_FiveMinuteRate',
    'pinot_controller_numberTimesScheduleTasksCalled_MeanRate': 'pinot_controller_numberTimesScheduleTasksCalled_MeanRate',
    'pinot_controller_numberTimesScheduleTasksCalled_OneMinuteRate': 'pinot_controller_numberTimesScheduleTasksCalled_OneMinuteRate',
    'pinot_controller_offlineTableCount_Value': 'pinot_controller_offlineTableCount_Value',
    'pinot_controller_onlineMinionInstances_Value': 'pinot_controller_onlineMinionInstances_Value',
    'pinot_controller_percentMinionSubtasksInError_Value': 'pinot_controller_percentMinionSubtasksInError_Value',
    'pinot_controller_percentMinionSubtasksInQueue_Value': 'pinot_controller_percentMinionSubtasksInQueue_Value',
    'pinot_controller_periodicTaskNumTablesProcessed_Value': 'pinot_controller_periodicTaskNumTablesProcessed_Value',
    'pinot_controller_pinotControllerLeader_Value': 'pinot_controller_pinotControllerLeader_Value',
    'pinot_controller_pinotLeadControllerResourceEnabled_Value': 'pinot_controller_pinotLeadControllerResourceEnabled_Value',
    'pinot_controller_realtimeTableCount_Value': 'pinot_controller_realtimeTableCount_Value',
    'pinot_controller_segmentDownloadsInProgress_Value': 'pinot_controller_segmentDownloadsInProgress_Value',
    'pinot_controller_segmentUploadsInProgress_Value': 'pinot_controller_segmentUploadsInProgress_Value',
    'pinot_controller_tableWithoutSchemaCount_Value': 'pinot_controller_tableWithoutSchemaCount_Value',
    'pinot_controller_tierBackendTableCount_Value': 'pinot_controller_tierBackendTableCount_Value',
    'pinot_controller_upsertTableCount_Value': 'pinot_controller_upsertTableCount_Value',
    'pinot_controller_version_Value': 'pinot_controller_version_Value',
}

# Server-specific metrics
SERVER_SPECIFIC_METRICS = {
    # Query limit metrics
    'pinot_server_aggregateTimesNumGroupsLimitReached_Count': 'pinot_server_aggregateTimesNumGroupsLimitReached_Count',
    'pinot_server_aggregateTimesNumGroupsLimitReached_FifteenMinuteRate': 'pinot_server_aggregateTimesNumGroupsLimitReached_FifteenMinuteRate',
    'pinot_server_aggregateTimesNumGroupsLimitReached_FiveMinuteRate': 'pinot_server_aggregateTimesNumGroupsLimitReached_FiveMinuteRate',
    'pinot_server_aggregateTimesNumGroupsLimitReached_MeanRate': 'pinot_server_aggregateTimesNumGroupsLimitReached_MeanRate',
    'pinot_server_aggregateTimesNumGroupsLimitReached_OneMinuteRate': 'pinot_server_aggregateTimesNumGroupsLimitReached_OneMinuteRate',
    # gRPC metrics
    'pinot_server_grpcBytesReceived_Count': 'pinot_server_grpcBytesReceived_Count',
    'pinot_server_grpcBytesReceived_FifteenMinuteRate': 'pinot_server_grpcBytesReceived_FifteenMinuteRate',
    'pinot_server_grpcBytesReceived_FiveMinuteRate': 'pinot_server_grpcBytesReceived_FiveMinuteRate',
    'pinot_server_grpcBytesReceived_MeanRate': 'pinot_server_grpcBytesReceived_MeanRate',
    'pinot_server_grpcBytesReceived_OneMinuteRate': 'pinot_server_grpcBytesReceived_OneMinuteRate',
    'pinot_server_grpcBytesSent_Count': 'pinot_server_grpcBytesSent_Count',
    'pinot_server_grpcBytesSent_FifteenMinuteRate': 'pinot_server_grpcBytesSent_FifteenMinuteRate',
    'pinot_server_grpcBytesSent_FiveMinuteRate': 'pinot_server_grpcBytesSent_FiveMinuteRate',
    'pinot_server_grpcBytesSent_MeanRate': 'pinot_server_grpcBytesSent_MeanRate',
    'pinot_server_grpcBytesSent_OneMinuteRate': 'pinot_server_grpcBytesSent_OneMinuteRate',
    'pinot_server_grpcQueries_Count': 'pinot_server_grpcQueries_Count',
    'pinot_server_grpcQueries_FifteenMinuteRate': 'pinot_server_grpcQueries_FifteenMinuteRate',
    'pinot_server_grpcQueries_FiveMinuteRate': 'pinot_server_grpcQueries_FiveMinuteRate',
    'pinot_server_grpcQueries_MeanRate': 'pinot_server_grpcQueries_MeanRate',
    'pinot_server_grpcQueries_OneMinuteRate': 'pinot_server_grpcQueries_OneMinuteRate',
    # Heap metrics
    'pinot_server_heapCriticalLevelExceeded_Count': 'pinot_server_heapCriticalLevelExceeded_Count',
    'pinot_server_heapCriticalLevelExceeded_FifteenMinuteRate': 'pinot_server_heapCriticalLevelExceeded_FifteenMinuteRate',
    'pinot_server_heapCriticalLevelExceeded_FiveMinuteRate': 'pinot_server_heapCriticalLevelExceeded_FiveMinuteRate',
    'pinot_server_heapCriticalLevelExceeded_MeanRate': 'pinot_server_heapCriticalLevelExceeded_MeanRate',
    'pinot_server_heapCriticalLevelExceeded_OneMinuteRate': 'pinot_server_heapCriticalLevelExceeded_OneMinuteRate',
    'pinot_server_heapPanicLevelExceeded_Count': 'pinot_server_heapPanicLevelExceeded_Count',
    'pinot_server_heapPanicLevelExceeded_FifteenMinuteRate': 'pinot_server_heapPanicLevelExceeded_FifteenMinuteRate',
    'pinot_server_heapPanicLevelExceeded_FiveMinuteRate': 'pinot_server_heapPanicLevelExceeded_FiveMinuteRate',
    'pinot_server_heapPanicLevelExceeded_MeanRate': 'pinot_server_heapPanicLevelExceeded_MeanRate',
    'pinot_server_heapPanicLevelExceeded_OneMinuteRate': 'pinot_server_heapPanicLevelExceeded_OneMinuteRate',
    # Helix metrics
    'pinot_server_helix_connected_Value': 'pinot_server_helix_connected_Value',
    'pinot_server_helix_zookeeperReconnects_Count': 'pinot_server_helix_zookeeperReconnects_Count',
    'pinot_server_helix_zookeeperReconnects_FifteenMinuteRate': 'pinot_server_helix_zookeeperReconnects_FifteenMinuteRate',
    'pinot_server_helix_zookeeperReconnects_FiveMinuteRate': 'pinot_server_helix_zookeeperReconnects_FiveMinuteRate',
    'pinot_server_helix_zookeeperReconnects_MeanRate': 'pinot_server_helix_zookeeperReconnects_MeanRate',
    'pinot_server_helix_zookeeperReconnects_OneMinuteRate': 'pinot_server_helix_zookeeperReconnects_OneMinuteRate',
    # Query metrics
    'pinot_server_queries_Count': 'pinot_server_queries_Count',
    'pinot_server_queries_FifteenMinuteRate': 'pinot_server_queries_FifteenMinuteRate',
    'pinot_server_queries_FiveMinuteRate': 'pinot_server_queries_FiveMinuteRate',
    'pinot_server_queries_MeanRate': 'pinot_server_queries_MeanRate',
    'pinot_server_queries_OneMinuteRate': 'pinot_server_queries_OneMinuteRate',
    'pinot_server_queriesDisabled_Value': 'pinot_server_queriesDisabled_Value',
    'pinot_server_queriesKilled_Count': 'pinot_server_queriesKilled_Count',
    'pinot_server_queriesKilled_FifteenMinuteRate': 'pinot_server_queriesKilled_FifteenMinuteRate',
    'pinot_server_queriesKilled_FiveMinuteRate': 'pinot_server_queriesKilled_FiveMinuteRate',
    'pinot_server_queriesKilled_MeanRate': 'pinot_server_queriesKilled_MeanRate',
    'pinot_server_queriesKilled_OneMinuteRate': 'pinot_server_queriesKilled_OneMinuteRate',
    # Memory metrics
    'pinot_server_jvmHeapUsedBytes_Value': 'pinot_server_jvmHeapUsedBytes_Value',
    'pinot_server_memory_allocationFailureCount_Value': 'pinot_server_memory_allocationFailureCount_Value',
    'pinot_server_memory_directBufferCount_Value': 'pinot_server_memory_directBufferCount_Value',
    'pinot_server_memory_directBufferUsage_Value': 'pinot_server_memory_directBufferUsage_Value',
    'pinot_server_memory_mmapBufferCount_Value': 'pinot_server_memory_mmapBufferCount_Value',
    'pinot_server_memory_mmapBufferUsage_Value': 'pinot_server_memory_mmapBufferUsage_Value',
    # Netty metrics
    'pinot_server_nettyPooledArenasDirect_Value': 'pinot_server_nettyPooledArenasDirect_Value',
    'pinot_server_nettyPooledArenasHeap_Value': 'pinot_server_nettyPooledArenasHeap_Value',
    'pinot_server_nettyPooledUsedDirectMemory_Value': 'pinot_server_nettyPooledUsedDirectMemory_Value',
    'pinot_server_nettyPooledUsedHeapMemory_Value': 'pinot_server_nettyPooledUsedHeapMemory_Value',
    # Realtime consumption metrics
    'pinot_server_realtime_rowsConsumed_Count': 'pinot_server_realtime_rowsConsumed_Count',
    'pinot_server_realtime_rowsConsumed_FifteenMinuteRate': 'pinot_server_realtime_rowsConsumed_FifteenMinuteRate',
    'pinot_server_realtime_rowsConsumed_FiveMinuteRate': 'pinot_server_realtime_rowsConsumed_FiveMinuteRate',
    'pinot_server_realtime_rowsConsumed_MeanRate': 'pinot_server_realtime_rowsConsumed_MeanRate',
    'pinot_server_realtime_rowsConsumed_OneMinuteRate': 'pinot_server_realtime_rowsConsumed_OneMinuteRate',
    'pinot_server_realtime_consumptionExceptions_Count': 'pinot_server_realtime_consumptionExceptions_Count',
    'pinot_server_realtime_consumptionExceptions_FifteenMinuteRate': 'pinot_server_realtime_consumptionExceptions_FifteenMinuteRate',
    'pinot_server_realtime_consumptionExceptions_FiveMinuteRate': 'pinot_server_realtime_consumptionExceptions_FiveMinuteRate',
    'pinot_server_realtime_consumptionExceptions_MeanRate': 'pinot_server_realtime_consumptionExceptions_MeanRate',
    'pinot_server_realtime_consumptionExceptions_OneMinuteRate': 'pinot_server_realtime_consumptionExceptions_OneMinuteRate',
    # Version
    'pinot_server_version_Value': 'pinot_server_version_Value',
}

# Broker-specific metrics
BROKER_SPECIFIC_METRICS = {
    # Cluster change metrics
    'pinot_broker_clusterChangeQueueTime_50thPercentile': 'pinot_broker_clusterChangeQueueTime_50thPercentile',
    'pinot_broker_clusterChangeQueueTime_75thPercentile': 'pinot_broker_clusterChangeQueueTime_75thPercentile',
    'pinot_broker_clusterChangeQueueTime_95thPercentile': 'pinot_broker_clusterChangeQueueTime_95thPercentile',
    'pinot_broker_clusterChangeQueueTime_99thPercentile': 'pinot_broker_clusterChangeQueueTime_99thPercentile',
    'pinot_broker_clusterChangeQueueTime_Count': 'pinot_broker_clusterChangeQueueTime_Count',
    'pinot_broker_clusterChangeQueueTime_Mean': 'pinot_broker_clusterChangeQueueTime_Mean',
    # Exception metrics
    'pinot_broker_exceptions_queryRejected_Count': 'pinot_broker_exceptions_queryRejected_Count',
    'pinot_broker_exceptions_queryRejected_FifteenMinuteRate': 'pinot_broker_exceptions_queryRejected_FifteenMinuteRate',
    'pinot_broker_exceptions_queryRejected_FiveMinuteRate': 'pinot_broker_exceptions_queryRejected_FiveMinuteRate',
    'pinot_broker_exceptions_queryRejected_MeanRate': 'pinot_broker_exceptions_queryRejected_MeanRate',
    'pinot_broker_exceptions_queryRejected_OneMinuteRate': 'pinot_broker_exceptions_queryRejected_OneMinuteRate',
    'pinot_broker_exceptions_requestCompilation_Count': 'pinot_broker_exceptions_requestCompilation_Count',
    'pinot_broker_exceptions_requestCompilation_FifteenMinuteRate': 'pinot_broker_exceptions_requestCompilation_FifteenMinuteRate',
    'pinot_broker_exceptions_requestCompilation_FiveMinuteRate': 'pinot_broker_exceptions_requestCompilation_FiveMinuteRate',
    'pinot_broker_exceptions_requestCompilation_MeanRate': 'pinot_broker_exceptions_requestCompilation_MeanRate',
    'pinot_broker_exceptions_requestCompilation_OneMinuteRate': 'pinot_broker_exceptions_requestCompilation_OneMinuteRate',
    'pinot_broker_exceptions_resourceMissing_Count': 'pinot_broker_exceptions_resourceMissing_Count',
    'pinot_broker_exceptions_resourceMissing_FifteenMinuteRate': 'pinot_broker_exceptions_resourceMissing_FifteenMinuteRate',
    'pinot_broker_exceptions_resourceMissing_FiveMinuteRate': 'pinot_broker_exceptions_resourceMissing_FiveMinuteRate',
    'pinot_broker_exceptions_resourceMissing_MeanRate': 'pinot_broker_exceptions_resourceMissing_MeanRate',
    'pinot_broker_exceptions_resourceMissing_OneMinuteRate': 'pinot_broker_exceptions_resourceMissing_OneMinuteRate',
    # Healthcheck metrics
    'pinot_broker_healthcheck_BadCalls_Count': 'pinot_broker_healthcheck_BadCalls_Count',
    'pinot_broker_healthcheck_BadCalls_FifteenMinuteRate': 'pinot_broker_healthcheck_BadCalls_FifteenMinuteRate',
    'pinot_broker_healthcheck_BadCalls_FiveMinuteRate': 'pinot_broker_healthcheck_BadCalls_FiveMinuteRate',
    'pinot_broker_healthcheck_BadCalls_MeanRate': 'pinot_broker_healthcheck_BadCalls_MeanRate',
    'pinot_broker_healthcheck_BadCalls_OneMinuteRate': 'pinot_broker_healthcheck_BadCalls_OneMinuteRate',
    'pinot_broker_healthcheck_OkCalls_Count': 'pinot_broker_healthcheck_OkCalls_Count',
    'pinot_broker_healthcheck_OkCalls_FifteenMinuteRate': 'pinot_broker_healthcheck_OkCalls_FifteenMinuteRate',
    'pinot_broker_healthcheck_OkCalls_FiveMinuteRate': 'pinot_broker_healthcheck_OkCalls_FiveMinuteRate',
    'pinot_broker_healthcheck_OkCalls_MeanRate': 'pinot_broker_healthcheck_OkCalls_MeanRate',
    'pinot_broker_healthcheck_OkCalls_OneMinuteRate': 'pinot_broker_healthcheck_OkCalls_OneMinuteRate',
    # Heap metrics
    'pinot_broker_heapCriticalLevelExceeded_Count': 'pinot_broker_heapCriticalLevelExceeded_Count',
    'pinot_broker_heapCriticalLevelExceeded_FifteenMinuteRate': 'pinot_broker_heapCriticalLevelExceeded_FifteenMinuteRate',
    'pinot_broker_heapCriticalLevelExceeded_FiveMinuteRate': 'pinot_broker_heapCriticalLevelExceeded_FiveMinuteRate',
    'pinot_broker_heapCriticalLevelExceeded_MeanRate': 'pinot_broker_heapCriticalLevelExceeded_MeanRate',
    'pinot_broker_heapCriticalLevelExceeded_OneMinuteRate': 'pinot_broker_heapCriticalLevelExceeded_OneMinuteRate',
    # Helix metrics
    'pinot_broker_helix_connected_Value': 'pinot_broker_helix_connected_Value',
    'pinot_broker_helix_zookeeper_Reconnects_Count': 'pinot_broker_helix_zookeeper_Reconnects_Count',
    'pinot_broker_helix_zookeeper_Reconnects_FifteenMinuteRate': 'pinot_broker_helix_zookeeper_Reconnects_FifteenMinuteRate',
    'pinot_broker_helix_zookeeper_Reconnects_FiveMinuteRate': 'pinot_broker_helix_zookeeper_Reconnects_FiveMinuteRate',
    'pinot_broker_helix_zookeeper_Reconnects_MeanRate': 'pinot_broker_helix_zookeeper_Reconnects_MeanRate',
    'pinot_broker_helix_zookeeper_Reconnects_OneMinuteRate': 'pinot_broker_helix_zookeeper_Reconnects_OneMinuteRate',
    # Query metrics
    'pinot_broker_queriesKilled_Count': 'pinot_broker_queriesKilled_Count',
    'pinot_broker_queriesKilled_FifteenMinuteRate': 'pinot_broker_queriesKilled_FifteenMinuteRate',
    'pinot_broker_queriesKilled_FiveMinuteRate': 'pinot_broker_queriesKilled_FiveMinuteRate',
    'pinot_broker_queriesKilled_MeanRate': 'pinot_broker_queriesKilled_MeanRate',
    'pinot_broker_queriesKilled_OneMinuteRate': 'pinot_broker_queriesKilled_OneMinuteRate',
    'pinot_broker_queriesWithJoins_Count': 'pinot_broker_queriesWithJoins_Count',
    'pinot_broker_queriesWithJoins_FifteenMinuteRate': 'pinot_broker_queriesWithJoins_FifteenMinuteRate',
    'pinot_broker_queriesWithJoins_FiveMinuteRate': 'pinot_broker_queriesWithJoins_FiveMinuteRate',
    'pinot_broker_queriesWithJoins_MeanRate': 'pinot_broker_queriesWithJoins_MeanRate',
    'pinot_broker_queriesWithJoins_OneMinuteRate': 'pinot_broker_queriesWithJoins_OneMinuteRate',
    # JVM and memory
    'pinot_broker_jvmHeapUsedBytes_Value': 'pinot_broker_jvmHeapUsedBytes_Value',
    'pinot_broker_nettyPooledUsedDirectMemory_Value': 'pinot_broker_nettyPooledUsedDirectMemory_Value',
    'pinot_broker_nettyPooledUsedHeapMemory_Value': 'pinot_broker_nettyPooledUsedHeapMemory_Value',
    # Other
    'pinot_broker_unhealthyServers_Value': 'pinot_broker_unhealthyServers_Value',
    'pinot_broker_queryRateLimitDisabled_Value': 'pinot_broker_queryRateLimitDisabled_Value',
    'pinot_broker_version_Value': 'pinot_broker_version_Value',
}

# Minion-specific metrics
MINION_SPECIFIC_METRICS = {
    # Health check metrics
    'pinot_minion_healthCheckBadCalls_Count': 'pinot_minion_healthCheckBadCalls_Count',
    'pinot_minion_healthCheckBadCalls_FifteenMinuteRate': 'pinot_minion_healthCheckBadCalls_FifteenMinuteRate',
    'pinot_minion_healthCheckBadCalls_FiveMinuteRate': 'pinot_minion_healthCheckBadCalls_FiveMinuteRate',
    'pinot_minion_healthCheckBadCalls_MeanRate': 'pinot_minion_healthCheckBadCalls_MeanRate',
    'pinot_minion_healthCheckBadCalls_OneMinuteRate': 'pinot_minion_healthCheckBadCalls_OneMinuteRate',
    'pinot_minion_healthCheckGoodCalls_Count': 'pinot_minion_healthCheckGoodCalls_Count',
    'pinot_minion_healthCheckGoodCalls_FifteenMinuteRate': 'pinot_minion_healthCheckGoodCalls_FifteenMinuteRate',
    'pinot_minion_healthCheckGoodCalls_FiveMinuteRate': 'pinot_minion_healthCheckGoodCalls_FiveMinuteRate',
    'pinot_minion_healthCheckGoodCalls_MeanRate': 'pinot_minion_healthCheckGoodCalls_MeanRate',
    'pinot_minion_healthCheckGoodCalls_OneMinuteRate': 'pinot_minion_healthCheckGoodCalls_OneMinuteRate',
    # Helix and task metrics
    'pinot_minion_connected_Value': 'pinot_minion_connected_Value',
    'pinot_minion_numberOfTasks_Value': 'pinot_minion_numberOfTasks_Value',
    'pinot_minion_version_Value': 'pinot_minion_version_Value',
}


# Component metric maps
# Each component uses a different namespace (e.g., pinot.controller, pinot.server)
# so the component prefix is not needed in the metric names
CONTROLLER_METRICS = {
    **COMMON_METRICS,
    **CONTROLLER_SPECIFIC_METRICS,
}
SERVER_METRICS = {
    **COMMON_METRICS,
    **SERVER_SPECIFIC_METRICS,
}
BROKER_METRICS = {
    **COMMON_METRICS,
    **BROKER_SPECIFIC_METRICS,
}
MINION_METRICS = {
    **COMMON_METRICS,
    **MINION_SPECIFIC_METRICS,
}

# Endpoint to metrics mapping
ENDPOINTS_METRICS_MAP = {
    'controller_endpoint': CONTROLLER_METRICS,
    'server_endpoint': SERVER_METRICS,
    'broker_endpoint': BROKER_METRICS,
    'minion_endpoint': MINION_METRICS,
}

# Labels that conflict with reserved Datadog tags
RENAME_LABELS_MAP = {
    'version': 'pinot_version',
}
