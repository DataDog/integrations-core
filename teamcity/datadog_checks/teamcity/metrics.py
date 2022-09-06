# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

METRIC_MAP = {
    'agents_connected_authorized_number': 'agents.connected.authorized',
    'agents_running_builds_number': 'agents.running.builds',
    'buildConfigurations_active_number': 'build.configs.active',
    'buildConfigurations_composite_active_number': 'build.configs.composite.active',
    'buildConfigurations_number': 'build.configs',
    'build_messages_incoming_number': 'build.messages.incoming.number',
    'build_messages_processing_number': 'build.messages.processing.number',
    'build_queue_estimates_processing_number': 'build.queue.estimates.processing.number',
    'build_queue_incoming_number': 'build.queue.incoming.number',
    'build_queue_processing_number': 'build.queue.processing.number',
    'build_service_messages_number': 'build.service.messages.number',
    'build_triggers_execution_milliseconds': 'build.triggers.execution.milliseconds',
    'build_triggers_execution_milliseconds_count': 'build.triggers.execution.ms.count',
    'build_triggers_execution_milliseconds_total': 'build.triggers.execution.ms.total',
    'build_triggers_per_type_execution_milliseconds': 'build.triggers.per.type.execution.milliseconds',
    'build_triggers_per_type_execution_milliseconds_count': 'build.triggers.per.type.execution.milliseconds.count',
    'build_triggers_per_type_execution_milliseconds_total': 'build.triggers.per.type.execution.milliseconds.total',
    'builds_finished_number': 'builds.finished.number',
    'builds_number': 'builds',
    'builds_queued_number': 'builds.queued',
    'builds_running_number': 'builds.running',
    'builds_started_number': 'builds.started',
    'cpu_count_number': 'cpu.count',
    'cpu_usage_process_number': 'cpu.usage.process',
    'cpu_usage_system_number': 'cpu.usage.system',
    'database_connections_active_number': 'database.connections.active',
    'db_table_writes_number': 'db.table.writes.number',
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
    'finishingBuild_buildFinishDelay_milliseconds': 'finishingbuild.buildfinishdelay.milliseconds',
    'finishingBuild_buildFinishDelay_milliseconds_count': 'finishingbuild.buildfinishdelay.milliseconds',
    'finishingBuild_buildFinishDelay_milliseconds_total': 'finishingbuild.buildfinishdelay.milliseconds',
    'httpSessions_active_number': 'httpSessions.active',
    'http_requests_duration_milliseconds': 'http.requests.duration.milliseconds',
    'http_requests_duration_milliseconds_bucket': 'http.requests.duration.milliseconds',
    'http_requests_duration_milliseconds_count': 'http.requests.duration.milliseconds',
    'http_requests_duration_milliseconds_total': 'http.requests.duration.milliseconds',
    'io_build_log_reads_bytes': 'io.build.log.reads.bytes',
    'io_build_log_writes_bytes': 'io.build.log.writes.bytes',
    'io_build_patch_writes_bytes': 'io.build.patch.writes.bytes',
    'jvm_buffer_count_number': 'jvm.buffer.count',
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
    'node_tasks_accepted_number': 'node.tasks.accepted',
    'node_tasks_finished_number': 'node.tasks.finished.number',
    'node_tasks_pending_number': 'node.tasks.pending',
    'process_queue_milliseconds': 'process.queue.milliseconds',
    'process_queue_milliseconds_count': 'process.queue.milliseconds',
    'process_queue_milliseconds_total': 'process.queue.milliseconds',
    'process_queue_parts_milliseconds': 'process.queue.parts.milliseconds',
    'process_queue_parts_milliseconds_count': 'process.queue.parts.milliseconds',
    'process_queue_parts_milliseconds_total': 'process.queue.parts.milliseconds',
    'process_websocket_send_pending_messages_milliseconds': 'process.websocket.send.pending.messages.milliseconds',
    'process_websocket_send_pending_messages_milliseconds_count': 'process.websocket.send.pending.messages.milliseconds',
    'process_websocket_send_pending_messages_milliseconds_total': 'process.websocket.send.pending.messages.milliseconds',
    'projects_active_number': 'projects.active',
    'projects_number': 'projects',
    'pullRequests_batch_time_milliseconds': 'pullrequests.batch.time.milliseconds',
    'pullRequests_batch_time_milliseconds_count': 'pullrequests.batch.time.milliseconds',
    'pullRequests_batch_time_milliseconds_total': 'pullrequests.batch.time.milliseconds',
    'pullRequests_single_time_milliseconds': 'pullrequests.single.time.milliseconds',
    'pullRequests_single_time_milliseconds_count': 'pullrequests.single.time.milliseconds',
    'pullRequests_single_time_milliseconds_total': 'pullrequests.single.time.milliseconds',
    'queuedBuild_waitingTime_milliseconds': 'queuedbuild.waitingtime.milliseconds',
    'queuedBuild_waitingTime_milliseconds_count': 'queuedbuild.waitingtime.milliseconds',
    'queuedBuild_waitingTime_milliseconds_total': 'queuedbuild.waitingtime.milliseconds',
    'runningBuilds_numberOfUnprocessedMessages_number': 'runningBuildsOfUnprocessedMessages',
    'server_uptime_milliseconds': 'server.uptime.milliseconds',
    'startingBuild_buildStartDelay_milliseconds': 'startingbuild.buildstartdelay.milliseconds',
    'startingBuild_buildStartDelay_milliseconds_count': 'startingbuild.buildstartdelay.milliseconds',
    'startingBuild_buildStartDelay_milliseconds_total': 'startingbuild.buildstartdelay.milliseconds',
    'startingBuild_runBuildDelay_milliseconds': 'startingbuild.runbuilddelay.milliseconds',
    'startingBuild_runBuildDelay_milliseconds_count': 'startingbuild.runbuilddelay.milliseconds',
    'startingBuild_runBuildDelay_milliseconds_total': 'startingbuild.runbuilddelay.milliseconds',
    'system_load_average_1m_number': 'system.load.average.1m',
    'teamcity_cache_InvestigationTestRunsHolder_projectScopes_number': 'cache.InvestigationTestRunsHolder.projectScopes',  # noqa E501
    'teamcity_cache_InvestigationTestRunsHolder_testNames_number': 'cache.InvestigationTestRunsHolder.testNames',
    'teamcity_cache_InvestigationTestRunsHolder_testRuns_number': 'tcache.InvestigationTestRunsHolder.testRuns',
    'users_active_number': 'users.active',
    'vcsChangesCollection_delay_milliseconds': 'vcschangescollection.delay.milliseconds',
    'vcsChangesCollection_delay_milliseconds_count': 'vcschangescollection.delay.milliseconds',
    'vcsChangesCollection_delay_milliseconds_total': 'vcschangescollection.delay.milliseconds',
    'vcsRootInstances_active_number': 'vcsRootInstances.active',
    'vcsRoots_number': 'vcsRoots',
    'vcs_changes_checking_milliseconds': 'vcs.changes.checking.milliseconds',
    'vcs_changes_checking_milliseconds_count': 'vcs.changes.checking.milliseconds',
    'vcs_changes_checking_milliseconds_total': 'vcs.changes.checking.milliseconds',
    'vcs_get_current_state_calls_number': 'vcs.get.current.state.calls.number',
    'vcs_git_fetch_duration_milliseconds': 'vcs.git.fetch.duration.milliseconds',
    'vcs_git_fetch_duration_milliseconds_count': 'vcs.git.fetch.duration.milliseconds',
    'vcs_git_fetch_duration_milliseconds_total': 'vcs.git.fetch.duration.milliseconds',
}

SUMMARY_METRICS = {
    'build_triggers_execution_milliseconds': 'build.triggers.execution.milliseconds',
    'build_triggers_execution_milliseconds_count': 'build.triggers.execution.milliseconds',
    'build_triggers_execution_milliseconds_total': 'build.triggers.execution.milliseconds',
    'build_triggers_per_type_execution_milliseconds': 'build.triggers.per.type.execution.milliseconds',
    'build_triggers_per_type_execution_milliseconds_count': 'build.triggers.per.type.execution.milliseconds',
    'build_triggers_per_type_execution_milliseconds_total': 'build.triggers.per.type.execution.milliseconds',
    'finishingBuild_buildFinishDelay_milliseconds': 'finishingbuild.buildfinishdelay.milliseconds',
    'finishingBuild_buildFinishDelay_milliseconds_count': 'finishingbuild.buildfinishdelay.milliseconds',
    'finishingBuild_buildFinishDelay_milliseconds_total': 'finishingbuild.buildfinishdelay.milliseconds',
    'process_queue_milliseconds': 'process.queue.milliseconds',
    'process_queue_milliseconds_count': 'process.queue.milliseconds',
    'process_queue_milliseconds_total': 'process.queue.milliseconds',
    'process_queue_parts_milliseconds': 'process.queue.parts.milliseconds',
    'process_queue_parts_milliseconds_count': 'process.queue.parts.milliseconds',
    'process_queue_parts_milliseconds_total': 'process.queue.parts.milliseconds',
    'process_websocket_send_pending_messages_milliseconds': 'process.websocket.send.pending.messages.milliseconds',
    'process_websocket_send_pending_messages_milliseconds_count': 'process.websocket.send.pending.messages.milliseconds',
    'process_websocket_send_pending_messages_milliseconds_total': 'process.websocket.send.pending.messages.milliseconds',
    'pullRequests_batch_time_milliseconds': 'pullrequests.batch.time.milliseconds',
    'pullRequests_batch_time_milliseconds_count': 'pullrequests.batch.time.milliseconds',
    'pullRequests_batch_time_milliseconds_total': 'pullrequests.batch.time.milliseconds',
    'pullRequests_single_time_milliseconds': 'pullrequests.single.time.milliseconds',
    'pullRequests_single_time_milliseconds_count': 'pullrequests.single.time.milliseconds',
    'pullRequests_single_time_milliseconds_total': 'pullrequests.single.time.milliseconds',
    'queuedBuild_waitingTime_milliseconds': 'queuedbuild.waitingtime.milliseconds',
    'queuedBuild_waitingTime_milliseconds_count': 'queuedbuild.waitingtime.milliseconds',
    'queuedBuild_waitingTime_milliseconds_total': 'queuedbuild.waitingtime.milliseconds',
    'startingBuild_buildStartDelay_milliseconds': 'startingbuild.buildstartdelay.milliseconds',
    'startingBuild_buildStartDelay_milliseconds_count': 'startingbuild.buildstartdelay.milliseconds',
    'startingBuild_buildStartDelay_milliseconds_total': 'startingbuild.buildstartdelay.milliseconds',
    'startingBuild_runBuildDelay_milliseconds': 'startingbuild.runbuilddelay.milliseconds',
    'startingBuild_runBuildDelay_milliseconds_count': 'startingbuild.runbuilddelay.milliseconds',
    'startingBuild_runBuildDelay_milliseconds_total': 'startingbuild.runbuilddelay.milliseconds',
    'vcsChangesCollection_delay_milliseconds': 'vcschangescollection.delay.milliseconds',
    'vcsChangesCollection_delay_milliseconds_count': 'vcschangescollection.delay.milliseconds',
    'vcsChangesCollection_delay_milliseconds_total': 'vcschangescollection.delay.milliseconds',
    'vcs_changes_checking_milliseconds': 'vcs.changes.checking.milliseconds',
    'vcs_changes_checking_milliseconds_count': 'vcs.changes.checking.milliseconds',
    'vcs_changes_checking_milliseconds_total': 'vcs.changes.checking.milliseconds',
    'vcs_git_fetch_duration_milliseconds': 'vcs.git.fetch.duration.milliseconds',
    'vcs_git_fetch_duration_milliseconds_count': 'vcs.git.fetch.duration.milliseconds',
    'vcs_git_fetch_duration_milliseconds_total': 'vcs.git.fetch.duration.milliseconds',
}

SIMPLE_BUILD_STATS_METRICS = {
    'ArtifactsSize': {'name': 'artifacts_size', 'method': 'gauge'},
    'BuildDuration': {'name': 'build_duration', 'method': 'gauge'},
    'BuildDurationNetTime': {'name': 'build_duration.net_time', 'method': 'gauge'},
    'BuildTestStatus': {'name': 'build_test_status', 'method': 'gauge'},
    'InspectionStatsE': {'name': 'inspection_stats_e', 'method': 'gauge'},
    'InspectionStatsW': {'name': 'inspection_stats_w', 'method': 'gauge'},
    'PassedTestCount': {'name': 'passed_test_count', 'method': 'gauge'},
    'FailedTestCount': {'name': 'failed_test_count', 'method': 'gauge'},
    'serverSideBuildFinishing': {'name': 'server_side_build_finishing', 'method': 'gauge'},
    'SuccessRate': {'name': 'success_rate', 'method': 'gauge'},
    'TimeSpentInQueue': {'name': 'time_spent_in_queue', 'method': 'gauge'},
    'TotalTestCount': {'name': 'total_test_count', 'method': 'gauge'},
}

REGEX_BUILD_STATS_METRICS = [
    {
        'regex': r'buildStageDuration\:([\s\S]*)',
        'name': 'build_stage_duration',
        'tags': ('build_stage',),
        'method': 'gauge',
    },
    {
        'regex': r'queueWaitReason\:([\s\S]*)',
        'name': 'queue_wait_reason',
        'tags': ('reason',),
        'method': 'gauge',
    },
]


def build_metric(metric_name):
    additional_tags = []
    if metric_name in SIMPLE_BUILD_STATS_METRICS:
        metric_mapping = SIMPLE_BUILD_STATS_METRICS[metric_name]
        name = metric_mapping['name']
        method = metric_mapping['method']
    else:
        for regex in REGEX_BUILD_STATS_METRICS:
            results = re.findall(str(regex['regex']), metric_name)
            if len(results) > 0 and isinstance(results[0], tuple):
                tags_values = list(results[0])
            else:
                tags_values = results
            if len(tags_values) == len(regex['tags']):
                method = regex['method']
                name = str(regex['name'])
                for i in range(len(regex['tags'])):
                    additional_tags.append('{}:{}'.format(regex['tags'][i], tags_values[i]))
                break
        else:
            return None, [], method
    return name, additional_tags, method


def construct_metrics_config(metric_map):
    metrics = []
    for raw_metric_name, metric_name in metric_map.items():
        if raw_metric_name.endswith('_total'):
            raw_metric_name = raw_metric_name[:-6]
            new_raw_metric_name = '{}_sum'.format(raw_metric_name)
            config = {new_raw_metric_name: {'name': metric_name, 'type': 'summary'}}
        if raw_metric_name.endswith('_count'):
            config = {raw_metric_name: {'name': metric_name, 'type': 'summary'}}
        else:
            config = {raw_metric_name: {'name': metric_name}}
        metrics.append(config)

    return metrics
