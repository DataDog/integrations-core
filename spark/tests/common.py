# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from packaging import version

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
HOST = get_docker_hostname()
SPARK_VERSION_RAW = os.environ['SPARK_VERSION']
SPARK_VERSION = version.parse(SPARK_VERSION_RAW)

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
    'spark.stage.executor_cpu_time',
    'spark.stage.disk_bytes_spilled',
    'spark.executor.count',
    'spark.driver.rdd_blocks',
    'spark.driver.total_duration',
    'spark.stage.num_complete_tasks',
    'spark.driver.completed_tasks',
    'spark.driver.memory_used',
    'spark.stage.input_records',
    'spark.stage.memory_bytes_spilled',
    'spark.streaming.statistics.batch_duration',
    'spark.stage.shuffle_write_records',
    'spark.streaming.statistics.avg_input_rate',
    'spark.streaming.statistics.avg_scheduling_delay',
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
]

if SPARK_VERSION >= version.parse('3.0.0'):
    EXPECTED_E2E_METRICS.extend([
        'spark.stage.executor_deserialize_cpu_time',
        'spark.stage.executor_deserialize_time',
        'spark.stage.jvm_gc_time',
        'spark.stage.peak_execution_memory',
        'spark.stage.result_serialization_time',
        'spark.stage.result_size',
        'spark.stage.shuffle_fetch_wait_time',
        'spark.stage.shuffle_local_blocks_fetched',
        'spark.stage.shuffle_local_bytes_read',
        'spark.stage.shuffle_remote_blocks_fetched',
        'spark.stage.shuffle_remote_bytes_read',
        'spark.stage.shuffle_remote_bytes_read_to_disk',
        'spark.stage.shuffle_write_time',
    ])


INSTANCE_STANDALONE = {
    'spark_url': 'http://{}:8080'.format(HOST),
    'cluster_name': 'SparkCluster',
    'spark_cluster_mode': 'spark_standalone_mode',
}


INSTANCE_DRIVER = {
    'spark_url': 'http://{}:4040'.format(HOST),
    'cluster_name': 'SparkDriver',
    'spark_cluster_mode': 'spark_driver_mode',
}
