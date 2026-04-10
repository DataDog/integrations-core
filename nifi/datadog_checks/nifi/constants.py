# ABOUTME: Endpoint paths and constants for the NiFi REST API.
# ABOUTME: Centralized definitions used by the API client and check.

# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

ABOUT_ENDPOINT = '/flow/about'
ACCESS_TOKEN_ENDPOINT = '/access/token'
CLUSTER_SUMMARY_ENDPOINT = '/flow/cluster/summary'
SYSTEM_DIAGNOSTICS_ENDPOINT = '/system-diagnostics'
FLOW_STATUS_ENDPOINT = '/flow/status'
PROCESS_GROUP_STATUS_ENDPOINT = '/flow/process-groups/{}/status'
BULLETIN_BOARD_ENDPOINT = '/flow/bulletin-board'

BULLETIN_ALERT_TYPE = {'DEBUG': 'info', 'ERROR': 'error', 'INFO': 'info', 'WARNING': 'warning'}

BULLETIN_LEVEL_ORDER = {'DEBUG': 0, 'INFO': 1, 'WARNING': 2, 'ERROR': 3}

RUN_STATUS_MAP = {'Running': 1, 'Stopped': 0, 'Invalid': -1, 'Disabled': -2}

# Metric mappings: (api_key, metric_name)
# Each group is alphabetically ordered by api_key.

CONNECTION_METRICS = [
    ('bytesQueued', 'connection.queued_bytes'),
    ('flowFilesIn', 'connection.flowfiles_in'),
    ('flowFilesOut', 'connection.flowfiles_out'),
    ('flowFilesQueued', 'connection.queued_count'),
    ('percentUseBytes', 'connection.percent_use_bytes'),
    ('percentUseCount', 'connection.percent_use_count'),
]

FLOW_STATUS_METRICS = [
    ('activeThreadCount', 'flow.active_threads'),
    ('bytesQueued', 'flow.bytes_queued'),
    ('disabledCount', 'flow.disabled_count'),
    ('flowFilesQueued', 'flow.flowfiles_queued'),
    ('invalidCount', 'flow.invalid_count'),
    ('runningCount', 'flow.running_count'),
    ('stoppedCount', 'flow.stopped_count'),
]

PROCESS_GROUP_METRICS = [
    ('activeThreadCount', 'process_group.active_threads'),
    ('bytesQueued', 'process_group.bytes_queued'),
    ('bytesRead', 'process_group.bytes_read'),
    ('bytesWritten', 'process_group.bytes_written'),
    ('flowFilesQueued', 'process_group.flowfiles_queued'),
    ('flowFilesReceived', 'process_group.flowfiles_received'),
    ('flowFilesSent', 'process_group.flowfiles_sent'),
    ('flowFilesTransferred', 'process_group.flowfiles_transferred'),
]

PROCESSOR_METRICS = [
    ('activeThreadCount', 'processor.active_threads'),
    ('bytesRead', 'processor.bytes_read'),
    ('bytesWritten', 'processor.bytes_written'),
    ('flowFilesIn', 'processor.flowfiles_in'),
    ('flowFilesOut', 'processor.flowfiles_out'),
    ('taskCount', 'processor.task_count'),
    ('tasksDurationNanos', 'processor.processing_nanos'),
]

# Partial metric names — the caller supplies a prefix (e.g., 'system.flowfile_repo').
REPO_METRICS = [
    ('freeSpaceBytes', 'free_space'),
    ('usedSpaceBytes', 'used_space'),
]

SYSTEM_CPU_METRICS = [
    ('availableProcessors', 'system.cpu.available_processors'),
    ('processorLoadAverage', 'system.cpu.load_average'),
]

SYSTEM_GC_METRICS = [
    ('collectionCount', 'system.gc.collection_count'),
    ('collectionMillis', 'system.gc.collection_time'),
]

SYSTEM_JVM_METRICS = [
    ('daemonThreads', 'system.jvm.daemon_threads'),
    ('maxHeapBytes', 'system.jvm.heap_max'),
    ('totalThreads', 'system.jvm.total_threads'),
    ('usedHeapBytes', 'system.jvm.heap_used'),
    ('usedNonHeapBytes', 'system.jvm.non_heap_used'),
]
