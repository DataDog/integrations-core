# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
from copy import deepcopy

STANDARD_PROMETHEUS_METRICS = {
    'agents_connected_authorized_number': 'agents.connected.authorized',
    'agents_running_builds_number': 'agents.running.builds',
    'buildConfigurations_active_number': 'build.configs.active',
    'buildConfigurations_composite_active_number': 'build.configs.composite.active',
    'buildConfigurations_number': 'build.configs',
    'build_messages_incoming_number': 'build.messages.incoming',
    'build_messages_processing_number': 'build.messages.processing',
    'build_queue_estimates_processing_number': 'build.queue.estimates.processing',
    'build_queue_incoming_number': 'build.queue.incoming',
    'build_queue_processing_number': 'build.queue.processing',
    'build_service_messages_number': 'build.service.messages',
    'builds_finished_number': 'builds.finished',
    'builds_number': 'builds',
    'builds_queued_number': 'builds.queued',
    'builds_running_number': 'builds.running',
    'builds_started_number': 'builds.started',
    'building_hosted_agents_number': 'building_hosted_agents',
    'cloud_active_nodes_number': 'cloud.active_nodes',
    'cloud_agent_afterBuild_number': 'cloud.agent.active_duration_afterBuild',
    'cloud_agent_beforeBuild_number': 'cloud.agent.active_duration_beforeBuild',
    'cloud_agent_beforeRegister_number': 'cloud.agent.starting_duration_beforeRegister',
    'cloud_agent_betweenBuild_number': 'cloud.agent.active_duration_betweenBuilds',
    'cloud_agent_totalBuild_number': 'cloud.agent.total_build_duration',
    'cloud_agent_totalBuildBeforeFinish_number': 'cloud.agent.total_build_duration_beforeFinish',
    'cloud_agent_useless_number': 'cloud.agent.idle_duration',
    'cloud_build_stuckCanceled_number': 'cloud.build_stuck_canceled',
    'cloud_pluginsFailedToLoad_number': 'cloud.plugins.failed_loading',
    'cloud_server_lowMemory_gcUsageExceeded_number': 'cloud.server.gc_usage_exceeded_errors',
    'cloud_server_lowMemory_highTotal_number': 'cloud.server.high_total_memory_errors',
    'cloud_tccPluginLoaded_number': 'cloud.tcc_plugin_loaded',
    'cloud_images_count_number': 'cloud.images',
    'current_full_agent_waiting_instances_number': 'current_full_agent_wait_instances',
    'current_full_agent_waiting_time_total_number': 'current_full_agent_wait_time_total',
    'current_full_agent_waiting_time_max_number': 'current_full_agent_wait_time_max',
    'full_agent_waiting_time_quantile_number': 'full_agent_wait_time.quantile',
    'cpu_count_number': 'cpu.count',
    'cpu_usage_process_number': 'cpu.usage.process',
    'cpu_usage_system_number': 'cpu.usage.system',
    'database_connections_active_number': 'database.connections.active',
    'db_table_writes_number': 'db.table.writes',
    'diskUsage_artifacts_bytes': 'disk_usage.artifacts.bytes',
    'diskUsage_logs_bytes': 'disk_usage.logs.bytes',
    'executors_asyncXmlRpc_activeTasks_number': 'executors.asyncXmlRpc.activeTasks',
    'executors_asyncXmlRpc_completedTasks_number': 'executors.asyncXmlRpc.completedTasks',
    'executors_asyncXmlRpc_maxQueueCapacity_number': 'executors.asyncXmlRpc.maxQueueCapacity',
    'executors_asyncXmlRpc_poolSize_number': 'executors.asyncXmlRpc.poolSize',
    'executors_asyncXmlRpc_queuedTasks_number': 'executors.asyncXmlRpc.queuedTasks',
    'executors_asyncXmlRpc_rejectsCount_number': 'executors.asyncXmlRpc.rejectsCount',
    'executors_baseVcsExecutor_activeTasks_number': 'executors.baseVcsExecutor.activeTasks',
    'executors_baseVcsExecutor_completedTasks_number': 'executors.baseVcsExecutor.completedTasks',
    'executors_baseVcsExecutor_maxQueueCapacity_number': 'executors.baseVcsExecutor.maxQueueCapacity',
    'executors_baseVcsExecutor_poolSize_number': 'executors.baseVcsExecutor.poolSize',
    'executors_baseVcsExecutor_queuedTasks_number': 'executors.baseVcsExecutor.queuedTasks',
    'executors_baseVcsExecutor_rejectsCount_number': 'executors.baseVcsExecutor.rejectsCount',
    'executors_cleanupExecutor_activeTasks_number': 'executors.cleanupExecutor.activeTasks',
    'executors_cleanupExecutor_completedTasks_number': 'executors.cleanupExecutor.completedTasks',
    'executors_cleanupExecutor_maxQueueCapacity_number': 'executors.cleanupExecutor.maxQueueCapacity',
    'executors_cleanupExecutor_poolSize_number': 'executors.cleanupExecutor.poolSize',
    'executors_cleanupExecutor_queuedTasks_number': 'executors.cleanupExecutor.queuedTasks',
    'executors_cleanupExecutor_rejectsCount_number': 'executors.cleanupExecutor.rejectsCount',
    'executors_lowPriorityExecutor_activeTasks_number': 'executors.lowPriorityExecutor.activeTasks',
    'executors_lowPriorityExecutor_completedTasks_number': 'executors.lowPriorityExecutor.completedTasks',
    'executors_lowPriorityExecutor_maxQueueCapacity_number': 'executors.lowPriorityExecutor.maxQueueCapacity',
    'executors_lowPriorityExecutor_poolSize_number': 'executors.lowPriorityExecutor.poolSize',
    'executors_lowPriorityExecutor_queuedTasks_number': 'executors.lowPriorityExecutor.queuedTasks',
    'executors_lowPriorityExecutor_rejectsCount_number': 'executors.lowPriorityExecutor.rejectsCount',
    'executors_normalExecutor_activeTasks_number': 'executors.normalExecutor.activeTasks',
    'executors_normalExecutor_completedTasks_number': 'executors.normalExecutor.completedTasks',
    'executors_normalExecutor_maxQueueCapacity_number': 'executors.normalExecutor.maxQueueCapacity',
    'executors_normalExecutor_poolSize_number': 'executors.normalExecutor.poolSize',
    'executors_normalExecutor_queuedTasks_number': 'executors.normalExecutor.queuedTasks',
    'executors_normalExecutor_rejectsCount_number': 'executors.normalExecutor.rejectsCount',
    'executors_periodicalVcsExecutor_activeTasks_number': 'executors.periodicalVcsExecutor.activeTasks',
    'executors_periodicalVcsExecutor_completedTasks_number': 'executors.periodicalVcsExecutor.completedTasks',
    'executors_periodicalVcsExecutor_maxQueueCapacity_number': 'executors.periodicalVcsExecutor.maxQueueCapacity',
    'executors_periodicalVcsExecutor_poolSize_number': 'executors.periodicalVcsExecutor.poolSize',
    'executors_periodicalVcsExecutor_queuedTasks_number': 'executors.periodicalVcsExecutor.queuedTasks',
    'executors_periodicalVcsExecutor_rejectsCount_number': 'executors.periodicalVcsExecutor.rejectsCount',
    'executors_tomcatHttpThreadPool_activeTasks_number': 'executors.tomcatHttpThreadPool.activeTasks',
    'executors_tomcatHttpThreadPool_poolSize_number': 'executors.tomcatHttpThreadPool.poolSize',
    'executors_triggersExecutor_activeTasks_number': 'executors.triggersExecutor.activeTasks',
    'executors_triggersExecutor_completedTasks_number': 'executors.triggersExecutor.completedTasks',
    'executors_triggersExecutor_maxQueueCapacity_number': 'executors.triggersExecutor.maxQueueCapacity',
    'executors_triggersExecutor_poolSize_number': 'executors.triggersExecutor.poolSize',
    'executors_triggersExecutor_queuedTasks_number': 'executors.triggersExecutor.queuedTasks',
    'executors_triggersExecutor_rejectsCount_number': 'executors.triggersExecutor.rejectsCount',
    'httpSessions_active_number': 'httpSessions.active',
    'io_build_log_reads_bytes': 'io.build.log.reads.bytes',
    'io_build_log_writes_bytes': 'io.build.log.writes.bytes',
    'io_build_patch_writes_bytes': 'io.build.patch.writes.bytes',
    'jvm_buffer_count_number': 'jvm.buffers_count',
    'jvm_buffer_memory_used_bytes': 'jvm.buffer.memory.used.bytes',
    'jvm_buffer_total_capacity_bytes': 'jvm.buffer.total.capacity.bytes',
    'jvm_gc_count_number': 'jvm.gc.count',
    'jvm_gc_duration_total_milliseconds': 'jvm.gc.duration.total.milliseconds',
    'jvm_gc_live_data_size_bytes': 'jvm.gc.live.data.size.bytes',
    'jvm_gc_max_data_size_bytes': 'jvm.gc.max.data.size.bytes',
    'jvm_gc_memory_allocated_bytes': 'jvm.gc.memory.allocated.bytes',
    'jvm_gc_memory_promoted_bytes': 'jvm.gc.memory.promoted.bytes',
    'jvm_memory_committed_bytes': 'jvm.memory.committed.bytes',
    'jvm_memory_max_bytes': 'jvm.memory.max.bytes',
    'jvm_memory_used_bytes': 'jvm.memory.used.bytes',
    'jvm_threads_daemon_number': 'jvm.threads.daemon',
    'jvm_threads_number': 'jvm.threads',
    'node_events_unprocessed_number': 'node.events.unprocessed',
    'node_events_processing_number': 'node.events.processing',
    'node_events_publishing_number': 'node.events.publishing',
    'node_tasks_accepted_number': 'node.tasks.accepted',
    'node_tasks_finished_number': 'node.tasks.finished',
    'node_tasks_pending_number': 'node.tasks.pending',
    'projects_active_number': 'projects.active',
    'projects_number': 'projects',
    'runningBuilds_numberOfUnprocessedMessages_number': 'runningBuilds.UnprocessedMessages',
    'server_uptime_milliseconds': 'server.uptime.milliseconds',
    'system_load_average_1m_number': 'system.load.average.1m',
    'teamcity_cache_InvestigationTestRunsHolder_projectScopes_number': 'cache.InvestigationTestRunsHolder'
    '.projectScopes',
    'teamcity_cache_InvestigationTestRunsHolder_testNames_number': 'cache.InvestigationTestRunsHolder.testNames',
    'teamcity_cache_InvestigationTestRunsHolder_testRuns_number': 'cache.InvestigationTestRunsHolder.testRuns',
    'users_active_number': 'users.active',
    'vcsRootInstances_active_number': 'vcsRootInstances.active',
    'vcsRoots_number': 'vcsRoots',
    'vcs_get_current_state_calls_number': 'vcs.get.current.state.calls',
}

HISTOGRAM_METRICS = {'http_requests_duration_milliseconds': 'http.requests.duration.milliseconds'}

SUMMARY_METRICS = {
    'build_triggers_execution_milliseconds': 'build.triggers.execution.milliseconds',
    'build_triggers_per_type_execution_milliseconds': 'build.triggers.per.type.execution.milliseconds',
    'finishingBuild_buildFinishDelay_milliseconds': 'finishingBuild.buildFinishDelay.milliseconds',
    'full_agent_waiting_time_milliseconds': 'full.agent.waiting.time.milliseconds',
    'build_queue_optimization_time_milliseconds': 'build.queue.optimization.time.milliseconds',
    'process_queue_milliseconds': 'process.queue.milliseconds',
    'process_queue_parts_milliseconds': 'process.queue.parts.milliseconds',
    'process_websocket_send_pending_messages_milliseconds': 'process.websocket.send.pending.messages.milliseconds',
    'pullRequests_batch_time_milliseconds': 'pullRequests.batch.time.milliseconds',
    'pullRequests_single_time_milliseconds': 'pullRequests.single.time.milliseconds',
    'queuedBuild_waitingTime_milliseconds': 'queuedBuild.waitingTime.milliseconds',
    'startingBuild_buildStartDelay_milliseconds': 'startingBuild.buildStartDelay.milliseconds',
    'startingBuild_runBuildDelay_milliseconds': 'startingBuild.runBuildDelay.milliseconds',
    'vcs_changes_checking_milliseconds': 'vcs.changes.checking.milliseconds',
    'vcsChangesCollection_delay_milliseconds': 'vcsChangesCollection.delay.milliseconds',
    'vcs_git_fetch_duration_milliseconds': 'vcs.git.fetch.duration.milliseconds',
}

METRIC_MAP = deepcopy(STANDARD_PROMETHEUS_METRICS)
METRIC_MAP.update(HISTOGRAM_METRICS)
METRIC_MAP.update(SUMMARY_METRICS)

SIMPLE_BUILD_STATS_METRICS = {
    'ArtifactsSize': {'name': 'artifacts_size', 'metric_type': 'gauge'},
    'BuildDuration': {'name': 'build_duration', 'metric_type': 'gauge'},
    'BuildDurationNetTime': {'name': 'build_duration.net_time', 'metric_type': 'gauge'},
    'BuildTestStatus': {'name': 'build_test_status', 'metric_type': 'gauge'},
    'InspectionStatsE': {'name': 'inspection_stats_e', 'metric_type': 'gauge'},
    'InspectionStatsW': {'name': 'inspection_stats_w', 'metric_type': 'gauge'},
    'PassedTestCount': {'name': 'passed_test_count', 'metric_type': 'gauge'},
    'FailedTestCount': {'name': 'failed_test_count', 'metric_type': 'gauge'},
    'serverSideBuildFinishing': {'name': 'server_side_build_finishing', 'metric_type': 'gauge'},
    'SuccessRate': {'name': 'success_rate', 'metric_type': 'gauge'},
    'TimeSpentInQueue': {'name': 'time_spent_in_queue', 'metric_type': 'gauge'},
    'TotalTestCount': {'name': 'total_test_count', 'metric_type': 'gauge'},
    'VisibleArtifactsSize': {'name': 'visible_artifacts_size', 'metric_type': 'gauge'},
    'CodeCoverageB': {'name': 'code_coverage.blocks.pct', 'metric_type': 'gauge'},
    'CodeCoverageC': {'name': 'code_coverage.classes.pct', 'metric_type': 'gauge'},
    'CodeCoverageL': {'name': 'code_coverage.lines.pct', 'metric_type': 'gauge'},
    'CodeCoverageM': {'name': 'code_coverage.methods.pct', 'metric_type': 'gauge'},
    'CodeCoverageR': {'name': 'code_coverage.branches.pct', 'metric_type': 'gauge'},
    'CodeCoverageS': {'name': 'code_coverage.statements.pct', 'metric_type': 'gauge'},
    'CodeCoverageAbsBCovered': {'name': 'code_coverage.blocks.covered', 'metric_type': 'gauge'},
    'CodeCoverageAbsBTotal': {'name': 'code_coverage.blocks.total', 'metric_type': 'gauge'},
    'CodeCoverageAbsCCovered': {'name': 'code_coverage.classes.covered', 'metric_type': 'gauge'},
    'CodeCoverageAbsCTotal': {'name': 'code_coverage.classes.total', 'metric_type': 'gauge'},
    'CodeCoverageAbsLCovered': {'name': 'code_coverage.lines.covered', 'metric_type': 'gauge'},
    'CodeCoverageAbsLTotal': {'name': 'code_coverage.lines.total', 'metric_type': 'gauge'},
    'CodeCoverageAbsMCovered': {'name': 'code_coverage.methods.covered', 'metric_type': 'gauge'},
    'CodeCoverageAbsMTotal': {'name': 'code_coverage.methods.total', 'metric_type': 'gauge'},
    'CodeCoverageAbsRCovered': {'name': 'code_coverage.branches.covered', 'metric_type': 'gauge'},
    'CodeCoverageAbsRTotal': {'name': 'code_coverage.branches.total', 'metric_type': 'gauge'},
    'CodeCoverageAbsSCovered': {'name': 'code_coverage.statements.covered', 'metric_type': 'gauge'},
    'CodeCoverageAbsSTotal': {'name': 'code_coverage.statements.total', 'metric_type': 'gauge'},
    'DuplicatorStats': {'name': 'duplicator_stats', 'metric_type': 'gauge'},
    'IgnoredTestCount': {'name': 'ignored_test_count', 'metric_type': 'gauge'},
}

REGEX_BUILD_STATS_METRICS = [
    {
        'regex': r'buildStageDuration\:([\s\S]*)',
        'name': 'build_stage_duration',
        'tags': ('build_stage',),
        'metric_type': 'gauge',
    },
    {
        'regex': r'queueWaitReason\:([\s\S]*)',
        'name': 'queue_wait_reason',
        'tags': ('reason',),
        'metric_type': 'gauge',
    },
]


def build_metric(metric_name):
    additional_tags = []
    name = None
    metric_type = None
    if metric_name in SIMPLE_BUILD_STATS_METRICS:
        metric_mapping = SIMPLE_BUILD_STATS_METRICS[metric_name]
        name = metric_mapping['name']
        metric_type = metric_mapping['metric_type']
    else:
        for regex in REGEX_BUILD_STATS_METRICS:
            name = str(regex['name'])
            metric_type = regex['metric_type']
            results = re.findall(str(regex['regex']), metric_name)
            if len(results) == 0:
                continue
            if len(results) > 0 and isinstance(results[0], tuple):
                tags_values = list(results[0])
            else:
                tags_values = results
            if len(tags_values) == len(regex['tags']):
                for i in range(len(regex['tags'])):
                    additional_tags.append('{}:{}'.format(regex['tags'][i], tags_values[i]))
                return name, additional_tags, metric_type
            return name, tags_values, metric_type
    return name, additional_tags, metric_type
