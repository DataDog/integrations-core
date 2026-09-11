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

# --------------------------------------------------------------------------- #
# Kubernetes driver-mode instance                                              #
# --------------------------------------------------------------------------- #
#
# When running the e2e test on a disposable kind cluster, the Agent pod runs
# inside the cluster and reaches the Spark driver via in-cluster Service DNS.
# No port forwarding or custom_hosts mapping is needed.

K8S_SPARK_NAMESPACE = 'spark'
K8S_SPARK_DRIVER_SERVICE = f'spark-driver.{K8S_SPARK_NAMESPACE}.svc.cluster.local'

INSTANCE_DRIVER_K8S = {
    'spark_url': f'http://{K8S_SPARK_DRIVER_SERVICE}:4040',
    'cluster_name': 'SparkDriverK8s',
    'spark_cluster_mode': 'spark_driver_mode',
}

K8S_CLUSTER_TAGS = [
    'spark_cluster:SparkDriverK8s',
    'cluster_name:SparkDriverK8s',
]

# Metrics that should always be present in driver mode on k8s.  In ``local[N]``
# mode the driver process is also the only executor, so executor-level metrics
# are emitted from the driver UI's ``/executors`` endpoint.
EXPECTED_E2E_DRIVER_K8S_METRICS = [
    # spark.job.*
    'spark.job.count',
    'spark.job.num_tasks',
    'spark.job.num_active_tasks',
    'spark.job.num_completed_tasks',
    'spark.job.num_skipped_tasks',
    'spark.job.num_failed_tasks',
    'spark.job.num_active_stages',
    'spark.job.num_completed_stages',
    'spark.job.num_skipped_stages',
    'spark.job.num_failed_stages',
    # spark.stage.*
    'spark.stage.count',
    'spark.stage.num_active_tasks',
    'spark.stage.num_complete_tasks',
    'spark.stage.num_failed_tasks',
    'spark.stage.executor_run_time',
    'spark.stage.input_bytes',
    'spark.stage.input_records',
    'spark.stage.output_bytes',
    'spark.stage.output_records',
    'spark.stage.shuffle_read_bytes',
    'spark.stage.shuffle_read_records',
    'spark.stage.shuffle_write_bytes',
    'spark.stage.shuffle_write_records',
    'spark.stage.memory_bytes_spilled',
    'spark.stage.disk_bytes_spilled',
    # spark.driver.*
    'spark.driver.rdd_blocks',
    'spark.driver.memory_used',
    'spark.driver.disk_used',
    'spark.driver.active_tasks',
    'spark.driver.failed_tasks',
    'spark.driver.completed_tasks',
    'spark.driver.total_tasks',
    'spark.driver.total_duration',
    'spark.driver.total_input_bytes',
    'spark.driver.total_shuffle_read',
    'spark.driver.total_shuffle_write',
    'spark.driver.max_memory',
    'spark.driver.mem.used_on_heap_storage',
    'spark.driver.mem.used_off_heap_storage',
    'spark.driver.mem.total_on_heap_storage',
    'spark.driver.mem.total_off_heap_storage',
]

# Metrics that may or may not be present depending on timing and Spark version.
FLAKY_E2E_DRIVER_K8S_METRICS = [
    # spark.executor.* (optional in driver mode — the driver is the only
    # executor in local[N] mode, and not all executor metrics are emitted)
    'spark.executor.count',
    'spark.executor.rdd_blocks',
    'spark.executor.memory_used',
    'spark.executor.disk_used',
    'spark.executor.active_tasks',
    'spark.executor.failed_tasks',
    'spark.executor.completed_tasks',
    'spark.executor.total_tasks',
    'spark.executor.total_duration',
    'spark.executor.total_input_bytes',
    'spark.executor.total_shuffle_read',
    'spark.executor.total_shuffle_write',
    'spark.executor.max_memory',
    'spark.executor.mem.used_on_heap_storage',
    'spark.executor.mem.used_off_heap_storage',
    'spark.executor.mem.total_on_heap_storage',
    'spark.executor.mem.total_off_heap_storage',
    # spark.structured_streaming.* (optional — depends on streaming activity)
    'spark.structured_streaming.latency',
    'spark.structured_streaming.processing_rate',
    'spark.structured_streaming.rows_count',
    'spark.structured_streaming.used_bytes',
    'spark.structured_streaming.input_rate',
    'spark.streaming.statistics.avg_input_rate',
    'spark.streaming.statistics.avg_processing_time',
    'spark.streaming.statistics.avg_scheduling_delay',
    'spark.streaming.statistics.avg_total_delay',
    'spark.streaming.statistics.batch_duration',
    'spark.streaming.statistics.num_active_batches',
    'spark.streaming.statistics.num_active_receivers',
    'spark.streaming.statistics.num_inactive_receivers',
    'spark.streaming.statistics.num_processed_records',
    'spark.streaming.statistics.num_received_records',
    'spark.streaming.statistics.num_receivers',
    'spark.streaming.statistics.num_retained_completed_batches',
    'spark.streaming.statistics.num_total_completed_batches',
    # Peak memory metrics are only available in Spark 3.0+ after a GC cycle
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
