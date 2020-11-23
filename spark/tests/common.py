# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
HOST = get_docker_hostname()

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
