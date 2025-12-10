# (C) Datadog, Inc. 2010-2019
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os
import re

import pytest
import requests

# Make sure this expected metrics list is up to date with:
# - `dogstatsd_mapper_profiles` configuration from README.md
# - metadata.csv
EXPECTED_METRICS = [
    '<job_name>_end',
    '<job_name>_heartbeat_failure',
    '<job_name>_start',
    'celery.execute_command.failure',
    'celery.task_timeout_error',
    'collect_db_dags',
    'dag.<dag_id>.<task_id>.duration',
    'dag.<dag_id>.<task_id>.queued_duration',
    'dag.<dag_id>.<task_id>.scheduled_duration',
    'dag.callback_exceptions',
    'dag_file_processor_timeouts',
    'dag_file_refresh_error',
    'dag_processing.file_path_queue_size',
    'dag_processing.file_path_queue_update_count',
    'dag_processing.import_errors',
    'dag_processing.last_duration',
    'dag_processing.last_duration.<dag_file>',
    'dag_processing.last_num_of_db_queries.<dag_file>',
    'dag_processing.last_run.seconds_ago.<dag_file>',
    'dag_processing.manager_stalls',
    'dag_processing.other_callback_count',
    'dag_processing.processes',
    'dag_processing.processor_timeouts',
    'dag_processing.sla_callback_count',
    'dag_processing.total_parse_time',
    'dagbag_size',
    'dagrun.<dag_id>.first_task_scheduling_delay',
    'dagrun.dependency-check',
    'dagrun.dependency-check.<dag_id>',
    'dagrun.duration.failed',
    'dagrun.duration.failed.<dag_id>',
    'dagrun.duration.success',
    'dagrun.duration.success.<dag_id>',
    'dagrun.first_task_scheduling_delay',
    'dagrun.schedule_delay',
    'dagrun.schedule_delay.<dag_id>',
    'dataset.orphaned',
    'dataset.triggered_dagruns',
    'dataset.updates',
    'executor.open_slots',
    'executor.open_slots.<executor_class_name>',
    'executor.queued_tasks',
    'executor.queued_tasks.<executor_class_name>',
    'executor.running_tasks',
    'executor.running_tasks.<executor_class_name>',
    'kubernetes_executor.adopt_task_instances.duration',
    'kubernetes_executor.clear_not_launched_queued_tasks.duration',
    'local_task_job.task_exit',
    'local_task_job.task_exit.<job_id>.<dag_id>.<task_id>.<return_code>',
    'operator_failures',
    'operator_failures_<operator_name>',
    'operator_successes',
    'operator_successes_<operator_name>',
    'pool.deferred_slots',
    'pool.deferred_slots.<pool_name>',
    'pool.open_slots',
    'pool.open_slots.<pool_name>',
    'pool.queued_slots',
    'pool.queued_slots.<pool_name>',
    'pool.running_slots',
    'pool.running_slots.<pool_name>',
    'pool.scheduled_slots',
    'pool.scheduled_slots.<pool_name>',
    'pool.starving_tasks',
    'pool.starving_tasks.<pool_name>',
    'previously_succeeded',
    'scheduler.critical_section_busy',
    'scheduler.critical_section_duration',
    'scheduler.critical_section_query_duration',
    'scheduler.orphaned_tasks.adopted',
    'scheduler.orphaned_tasks.cleared',
    'scheduler.scheduler_loop_duration',
    'scheduler.tasks.executable',
    'scheduler.tasks.killed_externally',
    'scheduler.tasks.starving',
    'scheduler_heartbeat',
    'sla_callback_notification_failure',
    'sla_email_notification_failure',
    'sla_missed',
    'task.cpu_usage.<dag_id>.<task_id>',
    'task.duration',
    'task.mem_usage.<dag_id>.<task_id>',
    'task.queued_duration',
    'task.scheduled_duration',
    'task_instance_created',
    'task_instance_created_<operator_name>',
    'task_removed_from_dag',
    'task_removed_from_dag.<dag_id>',
    'task_restored_to_dag.<dag_id>',
    'ti.finish',
    'ti.finish.<dag_id>.<task_id>.<state>',
    'ti.start',
    'ti.start.<dag_id>.<task_id>',
    'ti_failures',
    'ti_successes',
    'triggerer_heartbeat',
    'triggers.blocked_main_thread',
    'triggers.failed',
    'triggers.running',
    'triggers.running.<hostname>',
    'triggers.succeeded',
    'zombies_killed',
]

METRIC_PATTERN = re.compile(r'^``([^`]+)``\s+(.*)', re.MULTILINE)


@pytest.mark.latest_metrics
def test_check_metrics_up_to_date():
    airflow_version = os.getenv('AIRFLOW_VERSION', '2.11.0')
    
    # Airflow 2.x uses tag-based URLs with path: docs/apache-airflow/administration-and-deployment/logging-monitoring/metrics.rst
    url = f'https://raw.githubusercontent.com/apache/airflow/refs/tags/{airflow_version}/docs/apache-airflow/administration-and-deployment/logging-monitoring/metrics.rst'
    
    resp = requests.get(url)
    content = resp.content.decode('utf-8')
    matches = METRIC_PATTERN.findall(content)

    # Printed only on failure for convenience.
    print("Metric from {} :".format(url))
    print("")
    for metric, desc in matches:
        print("{:50} {}".format(metric, desc))

    # Use set() to handle any duplicates in the docs (e.g., task_restored_to_dag.<dag_id> appears twice)
    metrics = sorted(set([m for m, desc in matches]))
    expected_metrics_sorted = sorted(set(EXPECTED_METRICS))
    assert expected_metrics_sorted == metrics
