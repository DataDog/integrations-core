# Agent Check: Airflow

## Overview

The Datadog Agent collects many metrics from Airflow, including those for:

- DAGs (Directed Acyclic Graphs): Number of DAG processes, DAG bag size, etc.
- Tasks: Task failures, successes, killed, etc.
- Pools: Open slots, used slots, etc.
- Executors: Open slots, queued tasks, running tasks, etc.

Metrics are collected through the [Airflow StatsD](https://airflow.apache.org/docs/stable/metrics.html) plugin and sent to Datadog's [DogStatsD][8].

In addition to metrics, the Datadog Agent also sends service checks related to Airflow's health.

## Setup

### Installation

All three steps below are needed for the Airflow integration to work properly. Before you begin, [install the Datadog Agent][9] version `>=6.17` or `>=7.17`, which includes the StatsD/DogStatsD mapping feature.

#### Step 1: Configure Airflow to collect health metrics and service checks

Configure the Airflow check included in the [Datadog Agent][2] package to collect health metrics and service checks.

Edit the `airflow.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your Airflow service checks. See the [sample airflow.d/conf.yaml][3] for all available configuration options.

#### Step 2: Connect Airflow to DogStatsD (included in the Datadog Agent) by using Airflow `statsd` feature to collect metrics

1. Install the [Airflow StatsD plugin][1].

   ```shell
   pip install 'apache-airflow[statsd]'
   ```

2. Update the Airflow configuration file `airflow.cfg` by adding the following configs:

   ```conf
   [scheduler]
   statsd_on = True
   statsd_host = localhost
   statsd_port = 8125
   statsd_prefix = airflow
   ```

3. Update the [Datadog Agent main configuration file][10] `datadog.yaml` by adding the following configs:

   ```yaml
   # dogstatsd_mapper_cache_size: 1000  # default to 1000
   dogstatsd_mapper_profiles:
     - name: airflow
       prefix: "airflow."
       mappings:
         - match: "airflow.*_start"
           name: "airflow.job.start"
           tags:
             job_name: "$1"
         - match: "airflow.*_end"
           name: "airflow.job.end"
           tags:
             job_name: "$1"
         - match: "airflow.operator_failures_*"
           name: "airflow.operator_failures"
           tags:
             operator_name: "$1"
         - match: "airflow.operator_successes_*"
           name: "airflow.operator_successes"
           tags:
             operator_name: "$1"
         - match: 'airflow\.dag_processing\.last_runtime\.(.*)'
           match_type: "regex"
           name: "airflow.dag_processing.last_runtime"
           tags:
             dag_file: "$1"
         - match: 'airflow\.dag_processing\.last_run\.seconds_ago\.(.*)'
           match_type: "regex"
           name: "airflow.dag_processing.last_run.seconds_ago"
           tags:
             dag_file: "$1"
         - match: 'airflow\.dag\.loading-duration\.(.*)'
           match_type: "regex"
           name: "airflow.dag.loading_duration"
           tags:
             dag_file: "$1"
         - match: "airflow.pool.open_slots.*"
           name: "airflow.pool.open_slots"
           tags:
             pool_name: "$1"
         - match: "airflow.pool.used_slots.*"
           name: "airflow.pool.used_slots"
           tags:
             pool_name: "$1"
         - match: "airflow.pool.starving_tasks.*"
           name: "airflow.pool.starving_tasks"
           tags:
             pool_name: "$1"
         - match: 'airflow\.dagrun\.dependency-check\.(.*)'
           match_type: "regex"
           name: "airflow.dagrun.dependency_check"
           tags:
             dag_id: "$1"
         - match: 'airflow\.dag\.(.*)\.([^.]*)\.duration'
           match_type: "regex"
           name: "airflow.dag.task.duration"
           tags:
             dag_id: "$1"
             task_id: "$2"
         - match: 'airflow\.dag_processing\.last_duration\.(.*)'
           match_type: "regex"
           name: "airflow.dag_processing.last_duration"
           tags:
             dag_file: "$1"
         - match: 'airflow\.dagrun\.duration\.success\.(.*)'
           match_type: "regex"
           name: "airflow.dagrun.duration.success"
           tags:
             dag_id: "$1"
         - match: 'airflow\.dagrun\.duration\.failed\.(.*)'
           match_type: "regex"
           name: "airflow.dagrun.duration.failed"
           tags:
             dag_id: "$1"
         - match: 'airflow\.dagrun\.schedule_delay\.(.*)'
           match_type: "regex"
           name: "airflow.dagrun.schedule_delay"
           tags:
             dag_id: "$1"
         - match: 'airflow\.task_removed_from_dag\.(.*)'
           match_type: "regex"
           name: "airflow.dag.task_removed"
           tags:
             dag_id: "$1"
         - match: 'airflow\.task_restored_to_dag\.(.*)'
           match_type: "regex"
           name: "airflow.dag.task_restored"
           tags:
             dag_id: "$1"
         - match: "airflow.task_instance_created-*"
           name: "airflow.task.instance_created"
           tags:
             task_class: "$1"
   ```

#### Step 3: Restart Datadog Agent and Airflow

1. [Restart the Agent][4].
2. Restart Airflow to start sending your Airflow metrics to the Agent DogStatsD endpoint.

#### Integration Service Checks

Use the default configuration of your `airflow.d/conf.yaml` file to activate the collection of your Airflow service checks. See the sample [airflow.d/conf.yaml][3] for all available configuration options.

#### Log collection

_Available for Agent versions >6.0_

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

2. Uncomment and edit this configuration block at the bottom of your `airflow.d/conf.yaml`:

   Change the `path` and `service` parameter values and configure them for your environment.

   a. Configuration for DAG processor manager and Scheduler logs:

     ```yaml
     logs:
       - type: file
         path: '<PATH_TO_AIRFLOW>/logs/dag_processor_manager/dag_processor_manager.log'
         source: airflow
         service: '<SERVICE_NAME>'
         log_processing_rules:
           - type: multi_line
             name: new_log_start_with_date
             pattern: \[\d{4}\-\d{2}\-\d{2}
       - type: file
         path: '<PATH_TO_AIRFLOW>/logs/scheduler/*/*.log'
         source: airflow
         service: '<SERVICE_NAME>'
         log_processing_rules:
           - type: multi_line
             name: new_log_start_with_date
             pattern: \[\d{4}\-\d{2}\-\d{2}
     ```

     Regular clean up is recommended for scheduler logs with daily log rotation.

   b. Additional configuration for DAG tasks logs:

     ```yaml
     logs:
       - type: file
         path: '<PATH_TO_AIRFLOW>/logs/*/*/*/*.log'
         source: airflow
         service: '<SERVICE_NAME>'
         log_processing_rules:
           - type: multi_line
             name: new_log_start_with_date
             pattern: \[\d{4}\-\d{2}\-\d{2}
     ```

     Caveat: By default Airflow uses this log file template for tasks: `log_filename_template = {{ ti.dag_id }}/{{ ti.task_id }}/{{ ts }}/{{   try_number }}.log`. The number of log files will grow quickly if not cleaned regularly. This pattern is used by Airflow UI to display logs individually for each executed task.

     If you do not view logs in Airflow UI, Datadog recommends this configuration in `airflow.cfg`: `log_filename_template = dag_tasks.log`. Then log rotate this file and use this configuration:

     ```yaml
     logs:
       - type: file
         path: '<PATH_TO_AIRFLOW>/logs/dag_tasks.log'
         source: airflow
         service: '<SERVICE_NAME>'
         log_processing_rules:
           - type: multi_line
             name: new_log_start_with_date
             pattern: \[\d{4}\-\d{2}\-\d{2}
     ```

3. [Restart the Agent][7].

### Validation

[Run the Agent's status subcommand][5] and look for `airflow` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][6] for a list of metrics provided by this check.

### Service Checks

**airflow.can_connect**:

Returns `CRITICAL` if unable to connect to Airflow. Returns `OK` otherwise.

**airflow.healthy**:

Returns `CRITICAL` if Airflow is not healthy. Returns `OK` otherwise.

### Events

The Airflow check does not include any events.

## Annexe

### Airflow DatadogHook

In addition, [Airflow DatadogHook][11] can be used to interact with Datadog:

- Send Metric
- Query Metric
- Post Event

## Troubleshooting

Need help? Contact [Datadog support][7].

[1]: https://airflow.apache.org/docs/stable/metrics.html
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://github.com/DataDog/integrations-core/blob/master/airflow/datadog_checks/airflow/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/airflow/metadata.csv
[7]: https://docs.datadoghq.com/help/
[8]: https://docs.datadoghq.com/developers/dogstatsd/
[9]: https://docs.datadoghq.com/agent/
[10]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/
[11]: https://airflow.apache.org/docs/stable/_modules/airflow/contrib/hooks/datadog_hook.html
