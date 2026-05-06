# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
HOST = get_docker_hostname()

CLUSTER_NAME = 'SparkCluster'

CLUSTER_TAGS = [
    'spark_cluster:' + CLUSTER_NAME,
    'cluster_name:' + CLUSTER_NAME,
]

APP_NAME = 'PySparkShell'

YARN_APP_ID = 'application_1459362484344_0011'
SPARK_APP_ID = 'app_001'
SPARK_APP2_ID = 'app_002'

TEST_USERNAME = 'admin'
TEST_PASSWORD = 'password'

CUSTOM_TAGS = ['optional:tag1']
COMMON_TAGS = [
    'app_name:' + APP_NAME,
] + CLUSTER_TAGS

EXPECTED_E2E_METRICS = [
    'spark.driver.total_shuffle_read',
    'spark.stage.num_active_tasks',
    'spark.streaming.statistics.num_inactive_receivers',
    'spark.driver.max_memory',
    'spark.streaming.statistics.num_active_batches',
    'spark.driver.total_tasks',
    'spark.driver.failed_tasks',
    'spark.streaming.statistics.num_processed_records',
    'spark.stage.shuffle_read_records',
    'spark.streaming.statistics.num_receivers',
    'spark.stage.count',
    'spark.stage.num_failed_tasks',
    'spark.streaming.statistics.num_active_receivers',
    'spark.streaming.statistics.num_received_records',
    'spark.driver.active_tasks',
    'spark.stage.shuffle_read_bytes',
    'spark.stage.output_records',
    'spark.stage.shuffle_write_bytes',
    'spark.driver.total_shuffle_write',
    'spark.stage.output_bytes',
    'spark.stage.input_bytes',
    'spark.driver.disk_used',
    'spark.streaming.statistics.num_retained_completed_batches',
    'spark.driver.total_input_bytes',
    'spark.streaming.statistics.num_total_completed_batches',
    'spark.stage.executor_run_time',
    'spark.stage.disk_bytes_spilled',
    'spark.executor.count',
    'spark.driver.rdd_blocks',
    'spark.driver.total_duration',
    'spark.stage.num_complete_tasks',
    'spark.driver.completed_tasks',
    'spark.driver.memory_used',
    'spark.driver.mem.used_on_heap_storage',
    'spark.driver.mem.used_off_heap_storage',
    'spark.driver.mem.total_on_heap_storage',
    'spark.driver.mem.total_off_heap_storage',
    'spark.stage.input_records',
    'spark.stage.memory_bytes_spilled',
    'spark.streaming.statistics.batch_duration',
    'spark.stage.shuffle_write_records',
    'spark.job.num_completed_stages',
    'spark.job.count',
    'spark.job.num_tasks',
    'spark.job.num_active_stages',
    'spark.job.num_active_tasks',
    'spark.job.num_skipped_tasks',
    'spark.job.num_failed_stages',
    'spark.job.num_completed_tasks',
    'spark.job.num_skipped_stages',
    'spark.job.num_failed_tasks',
    'spark.executor.active_tasks',
    'spark.executor.completed_tasks',
    'spark.executor.disk_used',
    'spark.executor.failed_tasks',
    'spark.executor.max_memory',
    'spark.executor.memory_used',
    'spark.executor.mem.used_on_heap_storage',
    'spark.executor.mem.used_off_heap_storage',
    'spark.executor.mem.total_on_heap_storage',
    'spark.executor.mem.total_off_heap_storage',
    'spark.executor.rdd_blocks',
    'spark.executor.total_duration',
    'spark.executor.total_input_bytes',
    'spark.executor.total_shuffle_read',
    'spark.executor.total_shuffle_write',
    'spark.executor.total_tasks',
    'spark.structured_streaming.latency',
    'spark.structured_streaming.processing_rate',
    'spark.structured_streaming.rows_count',
    'spark.structured_streaming.used_bytes',
]

FLAKY_E2E_METRICS = [
    'spark.structured_streaming.input_rate',
    'spark.streaming.statistics.avg_input_rate',
    'spark.streaming.statistics.avg_scheduling_delay',
    # The peak memory metrics are only available in Spark 3.0+ and after one loop of garbage collection
    'spark.driver.peak_mem.jvm_heap_memory',
    'spark.driver.peak_mem.jvm_off_heap_memory',
    'spark.driver.peak_mem.on_heap_execution',
    'spark.driver.peak_mem.off_heap_execution',
    'spark.driver.peak_mem.on_heap_storage',
    'spark.driver.peak_mem.off_heap_storage',
    'spark.driver.peak_mem.on_heap_unified',
    'spark.driver.peak_mem.off_heap_unified',
    'spark.driver.peak_mem.direct_pool',
    'spark.driver.peak_mem.mapped_pool',
    'spark.driver.peak_mem.minor_gc_count',
    'spark.driver.peak_mem.minor_gc_time',
    'spark.driver.peak_mem.major_gc_count',
    'spark.driver.peak_mem.major_gc_time',
    'spark.driver.peak_mem.process_tree_jvm',
    'spark.driver.peak_mem.process_tree_jvm_rss',
    'spark.driver.peak_mem.process_tree_python',
    'spark.driver.peak_mem.process_tree_python_rss',
    'spark.driver.peak_mem.process_tree_other',
    'spark.driver.peak_mem.process_tree_other_rss',
    'spark.executor.peak_mem.jvm_heap_memory',
    'spark.executor.peak_mem.jvm_off_heap_memory',
    'spark.executor.peak_mem.on_heap_execution',
    'spark.executor.peak_mem.off_heap_execution',
    'spark.executor.peak_mem.on_heap_storage',
    'spark.executor.peak_mem.off_heap_storage',
    'spark.executor.peak_mem.on_heap_unified',
    'spark.executor.peak_mem.off_heap_unified',
    'spark.executor.peak_mem.direct_pool',
    'spark.executor.peak_mem.mapped_pool',
    'spark.executor.peak_mem.minor_gc_count',
    'spark.executor.peak_mem.minor_gc_time',
    'spark.executor.peak_mem.major_gc_count',
    'spark.executor.peak_mem.major_gc_time',
    'spark.executor.peak_mem.process_tree_jvm',
    'spark.executor.peak_mem.process_tree_jvm_rss',
    'spark.executor.peak_mem.process_tree_python',
    'spark.executor.peak_mem.process_tree_python_rss',
    'spark.executor.peak_mem.process_tree_other',
    'spark.executor.peak_mem.process_tree_other_rss',
]


INSTANCE_STANDALONE = {
    'spark_url': 'http://spark-master:8080',
    'cluster_name': 'SparkCluster',
    'spark_cluster_mode': 'spark_standalone_mode',
}


INSTANCE_DRIVER_1 = {
    'spark_url': 'http://spark-app-1:4040',
    'cluster_name': 'SparkDriver',
    'spark_cluster_mode': 'spark_driver_mode',
}

INSTANCE_DRIVER_2 = {
    'spark_url': 'http://spark-app-2:4050',
    'cluster_name': 'SparkDriver',
    'spark_cluster_mode': 'spark_driver_mode',
}

HOSTNAME_TO_PORT_MAPPING = {
    "spark-app-1": ('127.0.0.1', 4040),
    "spark-app-2": ('127.0.0.1', 4050),
    "spark-master": ('127.0.0.1', 8080),
}

SPARK_JOB_RUNNING_METRIC_VALUES = {
    'spark.job.count': 2,
    'spark.job.num_tasks': 20,
    'spark.job.num_active_tasks': 30,
    'spark.job.num_completed_tasks': 40,
    'spark.job.num_skipped_tasks': 50,
    'spark.job.num_failed_tasks': 60,
    'spark.job.num_active_stages': 70,
    'spark.job.num_completed_stages': 80,
    'spark.job.num_skipped_stages': 90,
    'spark.job.num_failed_stages': 100,
}

SPARK_JOB_RUNNING_METRIC_TAGS = [
    'status:running',
    'job_id:0',
    'stage_id:0',
    'stage_id:1',
] + COMMON_TAGS

SPARK_JOB_RUNNING_NO_STAGE_METRIC_TAGS = [
    'status:running',
    'job_id:0',
] + COMMON_TAGS

SPARK_JOB_SUCCEEDED_METRIC_VALUES = {
    'spark.job.count': 3,
    'spark.job.num_tasks': 1000,
    'spark.job.num_active_tasks': 2000,
    'spark.job.num_completed_tasks': 3000,
    'spark.job.num_skipped_tasks': 4000,
    'spark.job.num_failed_tasks': 5000,
    'spark.job.num_active_stages': 6000,
    'spark.job.num_completed_stages': 7000,
    'spark.job.num_skipped_stages': 8000,
    'spark.job.num_failed_stages': 9000,
}

SPARK_JOB_SUCCEEDED_METRIC_TAGS = [
    'status:succeeded',
    'job_id:0',
    'stage_id:0',
    'stage_id:1',
] + COMMON_TAGS

SPARK_JOB_SUCCEEDED_NO_STAGE_METRIC_TAGS = [
    'status:succeeded',
    'job_id:0',
] + COMMON_TAGS

SPARK_STAGE_RUNNING_METRIC_VALUES = {
    'spark.stage.count': 3,
    'spark.stage.num_active_tasks': 3 * 3,
    'spark.stage.num_complete_tasks': 4 * 3,
    'spark.stage.num_failed_tasks': 5 * 3,
    'spark.stage.executor_run_time': 6 * 3,
    'spark.stage.input_bytes': 7 * 3,
    'spark.stage.input_records': 8 * 3,
    'spark.stage.output_bytes': 9 * 3,
    'spark.stage.output_records': 10 * 3,
    'spark.stage.shuffle_read_bytes': 11 * 3,
    'spark.stage.shuffle_read_records': 12 * 3,
    'spark.stage.shuffle_write_bytes': 13 * 3,
    'spark.stage.shuffle_write_records': 14 * 3,
    'spark.stage.memory_bytes_spilled': 15 * 3,
    'spark.stage.disk_bytes_spilled': 16 * 3,
}

SPARK_STAGE_RUNNING_METRIC_TAGS = [
    'status:running',
    'stage_id:1',
] + COMMON_TAGS

SPARK_STAGE_COMPLETE_METRIC_VALUES = {
    'spark.stage.count': 2,
    'spark.stage.num_active_tasks': 100 * 2,
    'spark.stage.num_complete_tasks': 101 * 2,
    'spark.stage.num_failed_tasks': 102 * 2,
    'spark.stage.executor_run_time': 103 * 2,
    'spark.stage.input_bytes': 104 * 2,
    'spark.stage.input_records': 105 * 2,
    'spark.stage.output_bytes': 106 * 2,
    'spark.stage.output_records': 107 * 2,
    'spark.stage.shuffle_read_bytes': 108 * 2,
    'spark.stage.shuffle_read_records': 109 * 2,
    'spark.stage.shuffle_write_bytes': 110 * 2,
    'spark.stage.shuffle_write_records': 111 * 2,
    'spark.stage.memory_bytes_spilled': 112 * 2,
    'spark.stage.disk_bytes_spilled': 113 * 2,
}

SPARK_STAGE_COMPLETE_METRIC_TAGS = [
    'status:complete',
    'stage_id:0',
] + COMMON_TAGS

SPARK_DRIVER_METRIC_VALUES = {
    'spark.driver.rdd_blocks': 99,
    'spark.driver.memory_used': 98,
    'spark.driver.disk_used': 97,
    'spark.driver.active_tasks': 96,
    'spark.driver.failed_tasks': 95,
    'spark.driver.completed_tasks': 94,
    'spark.driver.total_tasks': 93,
    'spark.driver.total_duration': 92,
    'spark.driver.total_input_bytes': 91,
    'spark.driver.total_shuffle_read': 90,
    'spark.driver.total_shuffle_write': 89,
    'spark.driver.max_memory': 278019440,
    'spark.driver.mem.used_on_heap_storage': 79283,
    'spark.driver.mem.used_off_heap_storage': 0,
    'spark.driver.mem.total_on_heap_storage': 384093388,
    'spark.driver.mem.total_off_heap_storage': 0,
}

SPARK_DRIVER_OPTIONAL_METRIC_VALUES = {
    'spark.driver.peak_mem.jvm_heap_memory': 345498432,
    'spark.driver.peak_mem.jvm_off_heap_memory': 196924864,
    'spark.driver.peak_mem.on_heap_execution': 0,
    'spark.driver.peak_mem.off_heap_execution': 0,
    'spark.driver.peak_mem.on_heap_storage': 2445933,
    'spark.driver.peak_mem.off_heap_storage': 0,
    'spark.driver.peak_mem.on_heap_unified': 2445933,
    'spark.driver.peak_mem.off_heap_unified': 0,
    'spark.driver.peak_mem.direct_pool': 276762,
    'spark.driver.peak_mem.mapped_pool': 0,
    'spark.driver.peak_mem.minor_gc_count': 118,
    'spark.driver.peak_mem.minor_gc_time': 1436,
    'spark.driver.peak_mem.major_gc_count': 4,
    'spark.driver.peak_mem.major_gc_time': 419,
    'spark.driver.peak_mem.process_tree_jvm': 0,
    'spark.driver.peak_mem.process_tree_jvm_rss': 0,
    'spark.driver.peak_mem.process_tree_python': 0,
    'spark.driver.peak_mem.process_tree_python_rss': 0,
    'spark.driver.peak_mem.process_tree_other': 0,
    'spark.driver.peak_mem.process_tree_other_rss': 0,
}

SPARK_EXECUTOR_METRIC_VALUES = {
    'spark.executor.count': 2,
    'spark.executor.rdd_blocks': 1,
    'spark.executor.memory_used': 2,
    'spark.executor.disk_used': 3,
    'spark.executor.active_tasks': 4,
    'spark.executor.failed_tasks': 5,
    'spark.executor.completed_tasks': 6,
    'spark.executor.total_tasks': 7,
    'spark.executor.total_duration': 8,
    'spark.executor.total_input_bytes': 9,
    'spark.executor.total_shuffle_read': 10,
    'spark.executor.total_shuffle_write': 11,
    'spark.executor.max_memory': 555755765,
    'spark.executor.mem.used_on_heap_storage': 79283,
    'spark.executor.mem.used_off_heap_storage': 0,
    'spark.executor.mem.total_on_heap_storage': 384093388,
    'spark.executor.mem.total_off_heap_storage': 0,
}

SPARK_EXECUTOR_OPTIONAL_METRIC_VALUES = {
    'spark.executor.peak_mem.jvm_heap_memory': 361970928,
    'spark.executor.peak_mem.jvm_off_heap_memory': 94409256,
    'spark.executor.peak_mem.on_heap_execution': 16777216,
    'spark.executor.peak_mem.off_heap_execution': 0,
    'spark.executor.peak_mem.on_heap_storage': 2181737,
    'spark.executor.peak_mem.off_heap_storage': 0,
    'spark.executor.peak_mem.on_heap_unified': 18958953,
    'spark.executor.peak_mem.off_heap_unified': 0,
    'spark.executor.peak_mem.direct_pool': 8710,
    'spark.executor.peak_mem.mapped_pool': 0,
    'spark.executor.peak_mem.minor_gc_count': 988,
    'spark.executor.peak_mem.minor_gc_time': 5670,
    'spark.executor.peak_mem.major_gc_count': 3,
    'spark.executor.peak_mem.major_gc_time': 252,
    'spark.executor.peak_mem.process_tree_jvm': 0,
    'spark.executor.peak_mem.process_tree_jvm_rss': 0,
    'spark.executor.peak_mem.process_tree_python': 0,
    'spark.executor.peak_mem.process_tree_python_rss': 0,
    'spark.executor.peak_mem.process_tree_other': 0,
    'spark.executor.peak_mem.process_tree_other_rss': 0,
}

SPARK_EXECUTOR_LEVEL_METRIC_VALUES = {
    'spark.executor.id.rdd_blocks': 1,
    'spark.executor.id.memory_used': 2,
    'spark.executor.id.disk_used': 3,
    'spark.executor.id.active_tasks': 4,
    'spark.executor.id.failed_tasks': 5,
    'spark.executor.id.completed_tasks': 6,
    'spark.executor.id.total_tasks': 7,
    'spark.executor.id.total_duration': 8,
    'spark.executor.id.total_input_bytes': 9,
    'spark.executor.id.total_shuffle_read': 10,
    'spark.executor.id.total_shuffle_write': 11,
    'spark.executor.id.max_memory': 555755765,
    'spark.executor.id.mem.used_on_heap_storage': 79283,
    'spark.executor.id.mem.used_off_heap_storage': 0,
    'spark.executor.id.mem.total_on_heap_storage': 384093388,
    'spark.executor.id.mem.total_off_heap_storage': 0,
}

SPARK_EXECUTOR_LEVEL_OPTIONAL_PROCESS_TREE_METRIC_VALUES = {
    'spark.executor.id.peak_mem.jvm_heap_memory': 361970928,
    'spark.executor.id.peak_mem.jvm_off_heap_memory': 94409256,
    'spark.executor.id.peak_mem.on_heap_execution': 16777216,
    'spark.executor.id.peak_mem.off_heap_execution': 0,
    'spark.executor.id.peak_mem.on_heap_storage': 2181737,
    'spark.executor.id.peak_mem.off_heap_storage': 0,
    'spark.executor.id.peak_mem.on_heap_unified': 18958953,
    'spark.executor.id.peak_mem.off_heap_unified': 0,
    'spark.executor.id.peak_mem.direct_pool': 8710,
    'spark.executor.id.peak_mem.mapped_pool': 0,
    'spark.executor.id.peak_mem.minor_gc_count': 988,
    'spark.executor.id.peak_mem.minor_gc_time': 5670,
    'spark.executor.id.peak_mem.major_gc_count': 3,
    'spark.executor.id.peak_mem.major_gc_time': 252,
    'spark.executor.id.peak_mem.process_tree_jvm': 0,
    'spark.executor.id.peak_mem.process_tree_jvm_rss': 0,
    'spark.executor.id.peak_mem.process_tree_python': 0,
    'spark.executor.id.peak_mem.process_tree_python_rss': 0,
    'spark.executor.id.peak_mem.process_tree_other': 0,
    'spark.executor.id.peak_mem.process_tree_other_rss': 0,
}

SPARK_EXECUTOR_LEVEL_METRIC_TAGS = [
    'executor_id:1',
] + COMMON_TAGS

SPARK_RDD_METRIC_VALUES = {
    'spark.rdd.count': 1,
    'spark.rdd.num_partitions': 2,
    'spark.rdd.num_cached_partitions': 2,
    'spark.rdd.memory_used': 284,
    'spark.rdd.disk_used': 0,
}

SPARK_STREAMING_STATISTICS_METRIC_VALUES = {
    'spark.streaming.statistics.avg_input_rate': 1.0,
    'spark.streaming.statistics.avg_processing_time': 175,
    'spark.streaming.statistics.avg_scheduling_delay': 8,
    'spark.streaming.statistics.avg_total_delay': 183,
    'spark.streaming.statistics.batch_duration': 2000,
    'spark.streaming.statistics.num_active_batches': 2,
    'spark.streaming.statistics.num_active_receivers': 1,
    'spark.streaming.statistics.num_inactive_receivers': 3,
    'spark.streaming.statistics.num_processed_records': 7,
    'spark.streaming.statistics.num_received_records': 9,
    'spark.streaming.statistics.num_receivers': 10,
    'spark.streaming.statistics.num_retained_completed_batches': 27,
    'spark.streaming.statistics.num_total_completed_batches': 28,
}

SPARK_STRUCTURED_STREAMING_METRIC_VALUES = {
    'spark.structured_streaming.input_rate': 12,
    'spark.structured_streaming.latency': 12,
    'spark.structured_streaming.processing_rate': 12,
    'spark.structured_streaming.rows_count': 12,
    'spark.structured_streaming.used_bytes': 12,
}

SPARK_STRUCTURED_STREAMING_METRIC_NO_TAGS = {
    'spark.structured_streaming.input_rate',
    'spark.structured_streaming.latency',
}

SPARK_STRUCTURED_STREAMING_METRIC_PUNCTUATED_TAGS = {
    # Metric to test for punctuation in the query names of stream metrics.
    'spark.structured_streaming.input_rate': 100,
    'spark.structured_streaming.latency': 100,
    'spark.structured_streaming.processing_rate': 100,
}
