# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

from six import iteritems

# Identifier for cluster master address in `spark.yaml`
MASTER_ADDRESS = 'spark_url'
DEPRECATED_MASTER_ADDRESS = 'resourcemanager_uri'

# Switch that determines the mode Spark is running in. Can be either
# 'yarn' or 'standalone'
SPARK_CLUSTER_MODE = 'spark_cluster_mode'
SPARK_DRIVER_MODE = 'spark_driver_mode'
SPARK_YARN_MODE = 'spark_yarn_mode'
SPARK_STANDALONE_MODE = 'spark_standalone_mode'
SPARK_MESOS_MODE = 'spark_mesos_mode'

# option enabling compatibility mode for Spark ver < 2
SPARK_PRE_20_MODE = 'spark_pre_20_mode'

# Service Checks
SPARK_STANDALONE_SERVICE_CHECK = 'spark.standalone_master.can_connect'
SPARK_DRIVER_SERVICE_CHECK = 'spark.driver.can_connect'
YARN_SERVICE_CHECK = 'spark.resource_manager.can_connect'
SPARK_SERVICE_CHECK = 'spark.application_master.can_connect'
MESOS_SERVICE_CHECK = 'spark.mesos_master.can_connect'

# URL Paths
YARN_APPS_PATH = 'ws/v1/cluster/apps'
SPARK_APPS_PATH = 'api/v1/applications'
SPARK_VERSION_PATH = 'api/v1/version'
SPARK_MASTER_STATE_PATH = '/json/'
SPARK_MASTER_APP_PATH = '/app/'
MESOS_MASTER_APP_PATH = '/frameworks'

# Extract the application name and the dd metric name from the structured streams metrics.
STRUCTURED_STREAMS_METRICS_REGEX = re.compile(
    r"^[\w-]+\.driver\.spark\.streaming\.(?P<query_name>.+)\.(?P<metric_name>[\w-]+)$"
)

# Tests if the query_name is a UUID to determine whether to add it as a tag
# inspired by https://stackoverflow.com/questions/136505/searching-for-uuids-in-text-with-regex
UUID_REGEX = re.compile(r"[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}")

# Application type and states to collect
YARN_APPLICATION_TYPES = 'SPARK'
APPLICATION_STATES = 'RUNNING'

# Event types
JOB_EVENT = 'job'
STAGE_EVENT = 'stage'

# Alert types
ERROR_STATUS = 'FAILED'
SUCCESS_STATUS = ['SUCCEEDED', 'COMPLETE']

# Event source type
SOURCE_TYPE_NAME = 'spark'

# Metric types
GAUGE = 'gauge'
COUNT = 'count'
MONOTONIC_COUNT = 'monotonic_count'

# Metrics to collect
SPARK_JOB_METRICS = {
    'numTasks': ('spark.job.num_tasks', COUNT),
    'numActiveTasks': ('spark.job.num_active_tasks', COUNT),
    'numCompletedTasks': ('spark.job.num_completed_tasks', COUNT),
    'numSkippedTasks': ('spark.job.num_skipped_tasks', COUNT),
    'numFailedTasks': ('spark.job.num_failed_tasks', COUNT),
    'numActiveStages': ('spark.job.num_active_stages', COUNT),
    'numCompletedStages': ('spark.job.num_completed_stages', COUNT),
    'numSkippedStages': ('spark.job.num_skipped_stages', COUNT),
    'numFailedStages': ('spark.job.num_failed_stages', COUNT),
}

SPARK_STAGE_METRICS = {
    'numActiveTasks': ('spark.stage.num_active_tasks', COUNT),
    'numCompleteTasks': ('spark.stage.num_complete_tasks', COUNT),
    'numFailedTasks': ('spark.stage.num_failed_tasks', COUNT),
    'executorRunTime': ('spark.stage.executor_run_time', COUNT),
    'inputBytes': ('spark.stage.input_bytes', COUNT),
    'inputRecords': ('spark.stage.input_records', COUNT),
    'outputBytes': ('spark.stage.output_bytes', COUNT),
    'outputRecords': ('spark.stage.output_records', COUNT),
    'shuffleReadBytes': ('spark.stage.shuffle_read_bytes', COUNT),
    'shuffleReadRecords': ('spark.stage.shuffle_read_records', COUNT),
    'shuffleWriteBytes': ('spark.stage.shuffle_write_bytes', COUNT),
    'shuffleWriteRecords': ('spark.stage.shuffle_write_records', COUNT),
    'memoryBytesSpilled': ('spark.stage.memory_bytes_spilled', COUNT),
    'diskBytesSpilled': ('spark.stage.disk_bytes_spilled', COUNT),
}

SPARK_EXECUTOR_TEMPLATE_METRICS = {
    'rddBlocks': ('spark.{}.rdd_blocks', COUNT),
    'memoryUsed': ('spark.{}.memory_used', COUNT),
    'diskUsed': ('spark.{}.disk_used', COUNT),
    'activeTasks': ('spark.{}.active_tasks', COUNT),
    'failedTasks': ('spark.{}.failed_tasks', COUNT),
    'completedTasks': ('spark.{}.completed_tasks', COUNT),
    'totalTasks': ('spark.{}.total_tasks', COUNT),
    'totalDuration': ('spark.{}.total_duration', COUNT),
    'totalInputBytes': ('spark.{}.total_input_bytes', COUNT),
    'totalShuffleRead': ('spark.{}.total_shuffle_read', COUNT),
    'totalShuffleWrite': ('spark.{}.total_shuffle_write', COUNT),
    'maxMemory': ('spark.{}.max_memory', COUNT),
    # memoryMetrics is a dictionary of metrics
    'memoryMetrics.usedOnHeapStorageMemory': ('spark.{}.mem.used_on_heap_storage', COUNT),
    'memoryMetrics.usedOffHeapStorageMemory': ('spark.{}.mem.used_off_heap_storage', COUNT),
    'memoryMetrics.totalOnHeapStorageMemory': ('spark.{}.mem.total_on_heap_storage', COUNT),
    'memoryMetrics.totalOffHeapStorageMemory': ('spark.{}.mem.total_off_heap_storage', COUNT),
    # peakMemoryMetrics is a dictionary of metrics (available only in Spark 3.0+: https://issues.apache.org/jira/browse/SPARK-23429)
    'peakMemoryMetrics.JVMHeapMemory': ('spark.{}.peak_mem.jvm_heap_memory', COUNT),
    'peakMemoryMetrics.JVMOffHeapMemory': ('spark.{}.peak_mem.jvm_off_heap_memory', COUNT),
    'peakMemoryMetrics.OnHeapExecutionMemory': ('spark.{}.peak_mem.on_heap_execution', COUNT),
    'peakMemoryMetrics.OffHeapExecutionMemory': ('spark.{}.peak_mem.off_heap_execution', COUNT),
    'peakMemoryMetrics.OnHeapStorageMemory': ('spark.{}.peak_mem.on_heap_storage', COUNT),
    'peakMemoryMetrics.OffHeapStorageMemory': ('spark.{}.peak_mem.off_heap_storage', COUNT),
    'peakMemoryMetrics.OnHeapUnifiedMemory': ('spark.{}.peak_mem.on_heap_unified', COUNT),
    'peakMemoryMetrics.OffHeapUnifiedMemory': ('spark.{}.peak_mem.off_heap_unified', COUNT),
    'peakMemoryMetrics.DirectPoolMemory': ('spark.{}.peak_mem.direct_pool', COUNT),
    'peakMemoryMetrics.MappedPoolMemory': ('spark.{}.peak_mem.mapped_pool', COUNT),
    'peakMemoryMetrics.MinorGCCount': ('spark.{}.peak_mem.minor_gc_count', COUNT),
    'peakMemoryMetrics.MinorGCTime': ('spark.{}.peak_mem.minor_gc_time', COUNT),
    'peakMemoryMetrics.MajorGCCount': ('spark.{}.peak_mem.major_gc_count', COUNT),
    'peakMemoryMetrics.MajorGCTime': ('spark.{}.peak_mem.major_gc_time', COUNT),
    # Within peakMemoryMetrics, enabled if spark.executor.processTreeMetrics.enabled is true.
    'peakMemoryMetrics.ProcessTreeJVMVMemory': ('spark.{}.peak_mem.process_tree_jvm', COUNT),
    'peakMemoryMetrics.ProcessTreeJVMRSSMemory': ('spark.{}.peak_mem.process_tree_jvm_rss', COUNT),
    'peakMemoryMetrics.ProcessTreePythonVMemory': ('spark.{}.peak_mem.process_tree_python', COUNT),
    'peakMemoryMetrics.ProcessTreePythonRSSMemory': ('spark.{}.peak_mem.process_tree_python_rss', COUNT),
    'peakMemoryMetrics.ProcessTreeOtherVMemory': ('spark.{}.peak_mem.process_tree_other', COUNT),
    'peakMemoryMetrics.ProcessTreeOtherRSSMemory': ('spark.{}.peak_mem.process_tree_other_rss', COUNT),
}

SPARK_DRIVER_METRICS = {
    key: (value[0].format('driver'), value[1]) for key, value in iteritems(SPARK_EXECUTOR_TEMPLATE_METRICS)
}

SPARK_EXECUTOR_METRICS = {
    key: (value[0].format('executor'), value[1]) for key, value in iteritems(SPARK_EXECUTOR_TEMPLATE_METRICS)
}

SPARK_EXECUTOR_LEVEL_METRICS = {
    key: (value[0].format('executor.id'), value[1]) for key, value in iteritems(SPARK_EXECUTOR_TEMPLATE_METRICS)
}

SPARK_RDD_METRICS = {
    'numPartitions': ('spark.rdd.num_partitions', COUNT),
    'numCachedPartitions': ('spark.rdd.num_cached_partitions', COUNT),
    'memoryUsed': ('spark.rdd.memory_used', COUNT),
    'diskUsed': ('spark.rdd.disk_used', COUNT),
}

SPARK_STREAMING_STATISTICS_METRICS = {
    'avgInputRate': ('spark.streaming.statistics.avg_input_rate', GAUGE),
    'avgProcessingTime': ('spark.streaming.statistics.avg_processing_time', GAUGE),
    'avgSchedulingDelay': ('spark.streaming.statistics.avg_scheduling_delay', GAUGE),
    'avgTotalDelay': ('spark.streaming.statistics.avg_total_delay', GAUGE),
    'batchDuration': ('spark.streaming.statistics.batch_duration', GAUGE),
    'numActiveBatches': ('spark.streaming.statistics.num_active_batches', GAUGE),
    'numActiveReceivers': ('spark.streaming.statistics.num_active_receivers', GAUGE),
    'numInactiveReceivers': ('spark.streaming.statistics.num_inactive_receivers', GAUGE),
    'numProcessedRecords': ('spark.streaming.statistics.num_processed_records', MONOTONIC_COUNT),
    'numReceivedRecords': ('spark.streaming.statistics.num_received_records', MONOTONIC_COUNT),
    'numReceivers': ('spark.streaming.statistics.num_receivers', GAUGE),
    'numRetainedCompletedBatches': ('spark.streaming.statistics.num_retained_completed_batches', MONOTONIC_COUNT),
    'numTotalCompletedBatches': ('spark.streaming.statistics.num_total_completed_batches', MONOTONIC_COUNT),
}

SPARK_STRUCTURED_STREAMING_METRICS = {
    'inputRate-total': ('spark.structured_streaming.input_rate', GAUGE),
    'latency': ('spark.structured_streaming.latency', GAUGE),
    'processingRate-total': ('spark.structured_streaming.processing_rate', GAUGE),
    'states-rowsTotal': ('spark.structured_streaming.rows_count', GAUGE),
    'states-usedBytes': ('spark.structured_streaming.used_bytes', GAUGE),
}
