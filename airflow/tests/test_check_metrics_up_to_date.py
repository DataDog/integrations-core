# (C) Datadog, Inc. 2010-2019
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import re

import pytest
import requests

# Make sure this expected metrics list is up to date with:
# - `dogstatsd_mapper_profiles` configuration from README.md
# - metadata.csv
EXPECTED_METRICS = [
    '<job_name>_start',
    '<job_name>_end',
    '<job_name>_heartbeat_failure',
    'operator_failures_<operator_name>',
    'operator_successes_<operator_name>',
    'ti_failures',
    'ti_successes',
    'previously_succeeded',
    'zombies_killed',
    'scheduler_heartbeat',
    'dag_processing.processes',
    'dag_processing.manager_stalls',
    'dag_file_refresh_error',
    'scheduler.tasks.killed_externally',
    'scheduler.orphaned_tasks.cleared',
    'scheduler.orphaned_tasks.adopted',
    'scheduler.critical_section_busy',
    'sla_email_notification_failure',
    'ti.start.<dag_id>.<task_id>',
    'ti.finish.<dag_id>.<task_id>.<state>',
    'dag.callback_exceptions',
    'celery.task_timeout_error',
    'task_removed_from_dag.<dag_id>',
    'task_restored_to_dag.<dag_id>',
    'task_instance_created-<operator_name>',
    'dagbag_size',
    'dag_processing.import_errors',
    'dag_processing.total_parse_time',
    'dag_processing.last_runtime.<dag_file>',
    'dag_processing.last_run.seconds_ago.<dag_file>',
    'dag_processing.processor_timeouts',
    'scheduler.tasks.without_dagrun',
    'scheduler.tasks.running',
    'scheduler.tasks.starving',
    'scheduler.tasks.executable',
    'executor.open_slots',
    'executor.queued_tasks',
    'executor.running_tasks',
    'pool.open_slots.<pool_name>',
    'pool.queued_slots.<pool_name>',
    'pool.running_slots.<pool_name>',
    'pool.starving_tasks.<pool_name>',
    'smart_sensor_operator.poked_tasks',
    'smart_sensor_operator.poked_success',
    'smart_sensor_operator.poked_exception',
    'smart_sensor_operator.exception_failures',
    'smart_sensor_operator.infra_failures',
    # 'pool.used_slots.<pool_name>' appears on https://airflow.apache.org/docs/1.10.11/metrics.html
    'dagrun.dependency-check.<dag_id>',
    'dag.<dag_id>.<task_id>.duration',
    'dag_processing.last_duration.<dag_file>',
    'dagrun.duration.success.<dag_id>',
    'dagrun.duration.failed.<dag_id>',
    'dagrun.schedule_delay.<dag_id>',
    'scheduler.critical_section_duration',
    'dagrun.<dag_id>.first_task_scheduling_delay',
    'collect_db_dags',
]

METRIC_PATTERN = re.compile(r'^``([^`]+)``\s+(.*)', re.MULTILINE)


@pytest.mark.latest_metrics
def test_check_metrics_up_to_date():
    url = 'https://raw.githubusercontent.com/apache/airflow/master/docs/apache-airflow/logging-monitoring/metrics.rst'
    resp = requests.get(url)
    content = resp.content.decode('utf-8')
    matches = METRIC_PATTERN.findall(content)

    # Printed only on failure for convenience.
    print("Metric from {} :".format(url))
    print("")
    for metric, desc in matches:
        print("{:50} {}".format(metric, desc))

    metrics = [m for m, desc in matches]
    assert EXPECTED_METRICS == metrics
