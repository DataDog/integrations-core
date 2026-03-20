# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
# ruff: noqa: E501

# Common JVM metrics (shared across all components)
JVM_METRICS = {
    'jvm_buffer_pool_capacity_bytes': 'jvm_buffer_pool_capacity_bytes',
    'jvm_buffer_pool_used_bytes': 'jvm_buffer_pool_used_bytes',
    'jvm_gc_collection_seconds': 'jvm_gc_collection_seconds',
    'jvm_memory_bytes_max': 'jvm_memory_bytes_max',
    'jvm_memory_bytes_used': 'jvm_memory_bytes_used',
    'jvm_threads_current': 'jvm_threads_current',
}

# Common process metrics (shared across all components)
PROCESS_METRICS = {
    'process_cpu_seconds_total': 'process_cpu_seconds_total',
    'process_open_fds': 'process_open_fds',
}

# Common metrics shared across all components
COMMON_METRICS = {**JVM_METRICS, **PROCESS_METRICS}

# Controller-specific metrics
CONTROLLER_SPECIFIC_METRICS = {
    'pinot_controller_helix_connected_Value': 'pinot_controller_helix_connected_Value',
    'pinot_controller_helix_leader_Value': 'pinot_controller_helix_leader_Value',
    'pinot_controller_pinotControllerLeader_Value': 'pinot_controller_pinotControllerLeader_Value',
    'pinot_controller_exists_Value': 'pinot_controller_exists_Value',
    'pinot_controller_LeaderPartitionCount_Value': 'pinot_controller_LeaderPartitionCount_Value',
    'pinot_controller_offlineTableCount_Value': 'pinot_controller_offlineTableCount_Value',
    'pinot_controller_realtimeTableCount_Value': 'pinot_controller_realtimeTableCount_Value',
    'pinot_controller_disabledTableCount_Value': 'pinot_controller_disabledTableCount_Value',
    'pinot_controller_numMinionTasksInProgress_Value': 'pinot_controller_numMinionTasksInProgress_Value',
    'pinot_controller_numMinionSubtasksRunning_Value': 'pinot_controller_numMinionSubtasksRunning_Value',
    'pinot_controller_numMinionSubtasksWaiting_Value': 'pinot_controller_numMinionSubtasksWaiting_Value',
    'pinot_controller_numMinionSubtasksError_Value': 'pinot_controller_numMinionSubtasksError_Value',
    'pinot_controller_onlineMinionInstances_Value': 'pinot_controller_onlineMinionInstances_Value',
    'pinot_controller_segmentDownloadsInProgress_Value': 'pinot_controller_segmentDownloadsInProgress_Value',
    'pinot_controller_segmentUploadsInProgress_Value': 'pinot_controller_segmentUploadsInProgress_Value',
    'pinot_controller_InstanceDeleteError_Count': 'pinot_controller_InstanceDeleteError_Count',
    'pinot_controller_InstancePostError_Count': 'pinot_controller_InstancePostError_Count',
    'pinot_controller_TableUpdateError_Count': 'pinot_controller_TableUpdateError_Count',
    'pinot_controller_TableAddError_Count': 'pinot_controller_TableAddError_Count',
    'pinot_controller_TableSchemaUpdateError_Count': 'pinot_controller_TableSchemaUpdateError_Count',
    'pinot_controller_TableTenantCreateError_Count': 'pinot_controller_TableTenantCreateError_Count',
    'pinot_controller_TableTenantDeleteError_Count': 'pinot_controller_TableTenantDeleteError_Count',
    'pinot_controller_TableTenantUpdateError_Count': 'pinot_controller_TableTenantUpdateError_Count',
    'pinot_controller_SegmentUploadError_Count': 'pinot_controller_SegmentUploadError_Count',
    'pinot_controller_SchemaUploadError_Count': 'pinot_controller_SchemaUploadError_Count',
    'pinot_controller_RealtimeTableSegmentAssignmentError_Count': 'pinot_controller_RealtimeTableSegmentAssignmentError_Count',
    'pinot_controller_RealtimeTableSegmentAssignmentMismatch_Count': 'pinot_controller_RealtimeTableSegmentAssignmentMismatch_Count',
    'pinot_controller_numberSegmentUploadTimeoutExceeded_Count': 'pinot_controller_numberSegmentUploadTimeoutExceeded_Count',
    'pinot_controller_healthcheckOkCalls_Count': 'pinot_controller_healthcheckOkCalls_Count',
    'pinot_controller_healthcheckBadCalls_Count': 'pinot_controller_healthcheckBadCalls_Count',
    'pinot_controller_helix_ZookeeperReconnects_Count': 'pinot_controller_helix_ZookeeperReconnects_Count',
    'pinot_controller_LeadershipChangeWithoutCallback_Count': 'pinot_controller_LeadershipChangeWithoutCallback_Count',
    'pinot_controller_controllerPeriodicTaskRun_Count': 'pinot_controller_controllerPeriodicTaskRun_Count',
}

# Server-specific metrics
SERVER_SPECIFIC_METRICS = {
    'pinot_server_helix_connected_Value': 'pinot_server_helix_connected_Value',
    'pinot_server_jvmHeapUsedBytes_Value': 'pinot_server_jvmHeapUsedBytes_Value',
    'pinot_server_queriesDisabled_Value': 'pinot_server_queriesDisabled_Value',
    'pinot_server_memory_directBufferUsage_Value': 'pinot_server_memory_directBufferUsage_Value',
    'pinot_server_memory_mmapBufferUsage_Value': 'pinot_server_memory_mmapBufferUsage_Value',
    'pinot_server_memory_allocationFailureCount_Value': 'pinot_server_memory_allocationFailureCount_Value',
    'pinot_server_llcSimultaneousSegmentBuilds_Value': 'pinot_server_llcSimultaneousSegmentBuilds_Value',
    'pinot_server_queries_Count': 'pinot_server_queries_Count',
    'pinot_server_queriesKilled_Count': 'pinot_server_queriesKilled_Count',
    'pinot_server_indexingFailures_Count': 'pinot_server_indexingFailures_Count',
    'pinot_server_realtime_rowsConsumed_Count': 'pinot_server_realtime_rowsConsumed_Count',
    'pinot_server_realtimeRowsSanitized_Count': 'pinot_server_realtimeRowsSanitized_Count',
    'pinot_server_realtime_consumptionExceptions_Count': 'pinot_server_realtime_consumptionExceptions_Count',
    'pinot_server_realtime_exceptions_uncaught_Count': 'pinot_server_realtime_exceptions_uncaught_Count',
    'pinot_server_realtime_offsetCommits_Count': 'pinot_server_realtime_offsetCommits_Count',
    'pinot_server_helix_zookeeperReconnects_Count': 'pinot_server_helix_zookeeperReconnects_Count',
    'pinot_server_heapCriticalLevelExceeded_Count': 'pinot_server_heapCriticalLevelExceeded_Count',
    'pinot_server_grpcQueries_Count': 'pinot_server_grpcQueries_Count',
    'pinot_server_grpcBytesReceived_Count': 'pinot_server_grpcBytesReceived_Count',
    'pinot_server_grpcBytesSent_Count': 'pinot_server_grpcBytesSent_Count',
    'pinot_server_nettyConnection_BytesReceived_Count': 'pinot_server_nettyConnection_BytesReceived_Count',
    'pinot_server_nettyConnection_BytesSent_Count': 'pinot_server_nettyConnection_BytesSent_Count',
    'pinot_server_nettyConnection_ResponsesSent_Count': 'pinot_server_nettyConnection_ResponsesSent_Count',
    'pinot_server_readinessCheckOkCalls_Count': 'pinot_server_readinessCheckOkCalls_Count',
    'pinot_server_readinessCheckBadCalls_Count': 'pinot_server_readinessCheckBadCalls_Count',
    'pinot_server_noTableAccess_Count': 'pinot_server_noTableAccess_Count',
    'pinot_server_llcControllerResponse_Failed_Count': 'pinot_server_llcControllerResponse_Failed_Count',
    'pinot_server_llcControllerResponse_CommitSuccess_Count': 'pinot_server_llcControllerResponse_CommitSuccess_Count',
    'pinot_server_aggregateTimesNumGroupsLimitReached_Count': 'pinot_server_aggregateTimesNumGroupsLimitReached_Count',
    'pinot_server_windowTimesMaxRowsReached_Count': 'pinot_server_windowTimesMaxRowsReached_Count',
}

# Broker-specific metrics
BROKER_SPECIFIC_METRICS = {
    'pinot_broker_helix_connected_Value': 'pinot_broker_helix_connected_Value',
    'pinot_broker_unhealthyServers_Value': 'pinot_broker_unhealthyServers_Value',
    'pinot_broker_jvmHeapUsedBytes_Value': 'pinot_broker_jvmHeapUsedBytes_Value',
    'pinot_broker_nettyConnection_ConnectTimeMs_Value': 'pinot_broker_nettyConnection_ConnectTimeMs_Value',
    'pinot_broker_routingStatsManagerQueueSize_Value': 'pinot_broker_routingStatsManagerQueueSize_Value',
    'pinot_broker_queryRateLimitDisabled_Value': 'pinot_broker_queryRateLimitDisabled_Value',
    'pinot_broker_exceptions_queryRejected_Count': 'pinot_broker_exceptions_queryRejected_Count',
    'pinot_broker_exceptions_requestCompilation_Count': 'pinot_broker_exceptions_requestCompilation_Count',
    'pinot_broker_exceptions_resourceMissing_Count': 'pinot_broker_exceptions_resourceMissing_Count',
    'pinot_broker_exceptions_uncaughtGet_Count': 'pinot_broker_exceptions_uncaughtGet_Count',
    'pinot_broker_exceptions_uncaughtPost_Count': 'pinot_broker_exceptions_uncaughtPost_Count',
    'pinot_broker_healthcheck_BadCalls_Count': 'pinot_broker_healthcheck_BadCalls_Count',
    'pinot_broker_healthcheck_OkCalls_Count': 'pinot_broker_healthcheck_OkCalls_Count',
    'pinot_broker_heapCriticalLevelExceeded_Count': 'pinot_broker_heapCriticalLevelExceeded_Count',
    'pinot_broker_directMemoryOom_Count': 'pinot_broker_directMemoryOom_Count',
    'pinot_broker_helix_zookeeper_Reconnects_Count': 'pinot_broker_helix_zookeeper_Reconnects_Count',
    'pinot_broker_multiStageQueriesGlobal_Count': 'pinot_broker_multiStageQueriesGlobal_Count',
    'pinot_broker_queriesKilled_Count': 'pinot_broker_queriesKilled_Count',
    'pinot_broker_nettyConnection_BytesReceived_Count': 'pinot_broker_nettyConnection_BytesReceived_Count',
    'pinot_broker_nettyConnection_BytesSent_Count': 'pinot_broker_nettyConnection_BytesSent_Count',
    'pinot_broker_nettyConnection_RequestsSent_Count': 'pinot_broker_nettyConnection_RequestsSent_Count',
    'pinot_broker_clusterChangeQueueTime_99thPercentile': 'pinot_broker_clusterChangeQueueTime_99thPercentile',
}

# Minion-specific metrics
MINION_SPECIFIC_METRICS = {
    'pinot_minion_connected_Value': 'pinot_minion_connected_Value',
    'pinot_minion_numberOfTasks_Value': 'pinot_minion_numberOfTasks_Value',
    'pinot_minion_healthCheckBadCalls_Count': 'pinot_minion_healthCheckBadCalls_Count',
    'pinot_minion_healthCheckGoodCalls_Count': 'pinot_minion_healthCheckGoodCalls_Count',
}


# Component metric maps
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
