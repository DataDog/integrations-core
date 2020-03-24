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
    'operator_failures_<operator_name>',
    'operator_successes_<operator_name>',
    'ti_failures',
    'ti_successes',
    'zombies_killed',
    'scheduler_heartbeat',
    'dag_processing.processes',
    'scheduler.tasks.killed_externally',
    'dagbag_size',
    'dag_processing.import_errors',
    'dag_processing.total_parse_time',
    'dag_processing.last_runtime.<dag_file>',
    'dag_processing.last_run.seconds_ago.<dag_file>',
    'dag_processing.processor_timeouts',
    'executor.open_slots',
    'executor.queued_tasks',
    'executor.running_tasks',
    'pool.open_slots.<pool_name>',
    'pool.used_slots.<pool_name>',
    'pool.starving_tasks.<pool_name>',
    'dagrun.dependency-check.<dag_id>',
    'dag.<dag_id>.<task_id>.duration',
    'dag_processing.last_duration.<dag_file>',
    'dagrun.duration.success.<dag_id>',
    'dagrun.duration.failed.<dag_id>',
    'dagrun.schedule_delay.<dag_id>',
]

METRIC_PATTERN = re.compile(r'^``([^`]+)``\s+(.*)', re.MULTILINE)


@pytest.mark.check_metrics
def test_check_metrics_up_to_date():
    url = 'https://raw.githubusercontent.com/apache/airflow/master/docs/metrics.rst'
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
