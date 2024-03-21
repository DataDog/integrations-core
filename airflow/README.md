# Agent Check: Airflow

## Overview

The Datadog Agent collects many metrics from Airflow, including those for:

- DAGs (Directed Acyclic Graphs): Number of DAG processes, DAG bag size, etc.
- Tasks: Task failures, successes, killed, etc.
- Pools: Open slots, used slots, etc.
- Executors: Open slots, queued tasks, running tasks, etc.

Metrics are collected through the [Airflow StatsD][1] plugin and sent to Datadog's [DogStatsD][2].

In addition to metrics, the Datadog Agent also sends service checks related to Airflow's health.

## Setup

### Installation

All steps below are needed for the Airflow integration to work properly. Before you begin, [install the Datadog Agent][3] version `>=6.17` or `>=7.17`, which includes the StatsD/DogStatsD mapping feature.

### Configuration
There are two forms of the Airflow integration. There is the Datadog Agent integration which makes requests to a provided endpoint for Airflow to report whether it can connect and is healthy. Then there is the Airflow StatsD portion where Airflow can be configured to send metrics to the Datadog Agent, which can remap the Airflow notation to a Datadog notation.

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

##### Configure Datadog Agent Airflow integration

Configure the Airflow check included in the [Datadog Agent][4] package to collect health metrics and service checks. This can be done by editing the `url` within the `airflow.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory, to start collecting your Airflow service checks. See the [sample airflow.d/conf.yaml][5] for all available configuration options.

Ensure that `url` matches your Airflow [webserver `base_url`][19], the URL used to connect to your Airflow instance.

##### Connect Airflow to DogStatsD

Connect Airflow to DogStatsD (included in the Datadog Agent) by using the Airflow `statsd` feature to collect metrics. For more information about the metrics reported by the Airflow version used and the additional configuration options, see the Airflow documentation below:
- [Airflow Metrics][6]
- [Airflow Metrics Configuration][7]

**Note**: Presence or absence of StatsD metrics reported by Airflow might vary depending on the Airflow Executor used. For example: `airflow.ti_failures/successes`, `airflow.operator_failures/successes`, `airflow.dag.task.duration` are [not reported for `KubernetesExecutor`][20]. 

1. Install the [Airflow StatsD plugin][1].

   ```shell
   pip install 'apache-airflow[statsd]'
   ```

2. Update the Airflow configuration file `airflow.cfg` by adding the following configs:

   <div class="alert alert-warning"> Do not set `statsd_datadog_enabled` to true. Enabling `statsd_datadog_enabled` can create conflicts. To prevent issues, ensure that the variable is set to `False`.</div>
   
   ```conf
   [scheduler]
   statsd_on = True
   # Hostname or IP of server running the Datadog Agent
   statsd_host = localhost  
   # DogStatsD port configured in the Datadog Agent
   statsd_port = 8125
   statsd_prefix = airflow
   ```

3. Update the [Datadog Agent main configuration file][9] `datadog.yaml` by adding the following configs:

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
         - match: "airflow.*_heartbeat_failure"
           name: airflow.job.heartbeat.failure
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
         - match: "airflow.dagrun.*.first_task_scheduling_delay"
           name: "airflow.dagrun.first_task_scheduling_delay"
           tags:
             dag_id: "$1"
         - match: "airflow.pool.open_slots.*"
           name: "airflow.pool.open_slots"
           tags:
             pool_name: "$1"
         - match: "airflow.pool.queued_slots.*"
           name: "airflow.pool.queued_slots"
           tags:
             pool_name: "$1"
         - match: "airflow.pool.running_slots.*"
           name: "airflow.pool.running_slots"
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
         - match: 'airflow.scheduler.tasks.running'
           name: "airflow.scheduler.tasks.running"
         - match: 'airflow.scheduler.tasks.starving'
           name: "airflow.scheduler.tasks.starving"
         - match: 'airflow.sla_email_notification_failure'
           name: 'airflow.sla_email_notification_failure'
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
         - match: 'airflow\.ti\.start\.(.+)\.(\w+)'
           match_type: regex
           name: airflow.ti.start
           tags: 
             dag_id: "$1"
             task_id: "$2"
         - match: 'airflow\.ti\.finish\.(\w+)\.(.+)\.(\w+)'
           name: airflow.ti.finish
           match_type: regex
           tags: 
             dag_id: "$1"
             task_id: "$2"
             state: "$3"
   ```

##### Restart Datadog Agent and Airflow

1. [Restart the Agent][10].
2. Restart Airflow to start sending your Airflow metrics to the Agent DogStatsD endpoint.

##### Integration service checks

Use the default configuration in your `airflow.d/conf.yaml` file to activate your Airflow service checks. See the sample [airflow.d/conf.yaml][5] for all available configuration options.

##### Log collection

_Available for Agent versions >6.0_

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

2. Uncomment and edit this configuration block at the bottom of your `airflow.d/conf.yaml`:
  Change the `path` and `service` parameter values and configure them for your environment.

   - Configuration for DAG processor manager and Scheduler logs:

      ```yaml
      logs:
        - type: file
          path: "<PATH_TO_AIRFLOW>/logs/dag_processor_manager/dag_processor_manager.log"
          source: airflow
          log_processing_rules:
            - type: multi_line
              name: new_log_start_with_date
              pattern: \[\d{4}\-\d{2}\-\d{2}
        - type: file
          path: "<PATH_TO_AIRFLOW>/logs/scheduler/latest/*.log"
          source: airflow
          log_processing_rules:
            - type: multi_line
              name: new_log_start_with_date
              pattern: \[\d{4}\-\d{2}\-\d{2}
      ```

        Regular clean up is recommended for scheduler logs with daily log rotation.

   - Additional configuration for DAG tasks logs:

      ```yaml
      logs:
        - type: file
          path: "<PATH_TO_AIRFLOW>/logs/*/*/*/*.log"
          source: airflow
          log_processing_rules:
            - type: multi_line
              name: new_log_start_with_date
              pattern: \[\d{4}\-\d{2}\-\d{2}
      ```

      Caveat: By default Airflow uses this log file template for tasks: `log_filename_template = {{ ti.dag_id }}/{{ ti.task_id }}/{{ ts }}/{{ try_number }}.log`. The number of log files grow quickly if not cleaned regularly. This pattern is used by Airflow UI to display logs individually for each executed task.

      If you do not view logs in Airflow UI, Datadog recommends this configuration in `airflow.cfg`: `log_filename_template = dag_tasks.log`. Then log rotate this file and use this configuration:

      ```yaml
      logs:
        - type: file
          path: "<PATH_TO_AIRFLOW>/logs/dag_tasks.log"
          source: airflow
          log_processing_rules:
            - type: multi_line
              name: new_log_start_with_date
              pattern: \[\d{4}\-\d{2}\-\d{2}
      ```

3. [Restart the Agent][11].

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

##### Configure Datadog Agent Airflow integration

For containerized environments, see the [Autodiscovery Integration Templates][8] for guidance on applying the parameters below.

| Parameter            | Value                 |
|----------------------|-----------------------|
| `<INTEGRATION_NAME>` | `airflow`             |
| `<INIT_CONFIG>`      | blank or `{}`         |
| `<INSTANCE_CONFIG>`  | `{"url": "http://%%host%%:8080"}` |

Ensure that `url` matches your Airflow [webserver `base_url`][19], the URL used to connect to your Airflow instance. Replace `localhost` with the template variable `%%host%%`.

##### Connect Airflow to DogStatsD

Connect Airflow to DogStatsD (included in the Datadog Agent) by using the Airflow `statsd` feature to collect metrics. For more information about the metrics reported by the Airflow version used and the additional configuration options, see the Airflow documentation below:
- [Airflow Metrics][6]
- [Airflow Metrics Configuration][7]

**Note**: Presence or absence of StatsD metrics reported by Airflow might vary depending on the Airflow Executor used. For example: `airflow.ti_failures/successes`, `airflow.operator_failures/successes`, `airflow.dag.task.duration` are [not reported for `KubernetesExecutor`][20]. 

**Note**: The environment variables used for Airflow may differ between versions. For example in Airflow `2.0.0` this utilizes the environment variable `AIRFLOW__METRICS__STATSD_HOST`, whereas Airflow `1.10.15` utilizes `AIRFLOW__SCHEDULER__STATSD_HOST`. 

The Airflow StatsD configuration can be enabled with the following environment variables in a Kubernetes Deployment:
  ```yaml
  env:
    - name: AIRFLOW__SCHEDULER__STATSD_ON
      value: "True"
    - name: AIRFLOW__SCHEDULER__STATSD_PORT
      value: "8125"
    - name: AIRFLOW__SCHEDULER__STATSD_PREFIX
      value: "airflow"
    - name: AIRFLOW__SCHEDULER__STATSD_HOST
      valueFrom:
        fieldRef:
          fieldPath: status.hostIP
  ```
The environment variable for the host endpoint `AIRFLOW__SCHEDULER__STATSD_HOST` is supplied with the node's host IP address to route the StatsD data to the Datadog Agent pod on the same node as the Airflow pod. This setup also requires the Agent to have a `hostPort` open for this port `8125` and accepting non-local StatsD traffic. For more information, see [DogStatsD on Kubernetes Setup][12].

This should direct the StatsD traffic from the Airflow container to a Datadog Agent ready to accept the incoming data. The last portion is to update the Datadog Agent with the corresponding `dogstatsd_mapper_profiles` . This can be done by copying the `dogstatsd_mapper_profiles` provided in the [Host installation][13] into your `datadog.yaml` file. Or by deploying your Datadog Agent with the equivalent JSON configuration in the environment variable `DD_DOGSTATSD_MAPPER_PROFILES`. With respect to Kubernetes the equivalent environment variable notation is:
  ```yaml
  env: 
    - name: DD_DOGSTATSD_MAPPER_PROFILES
      value: >
        [{"name":"airflow","prefix":"airflow.","mappings":[{"match":"airflow.*_start","name":"airflow.job.start","tags":{"job_name":"$1"}},{"match":"airflow.*_end","name":"airflow.job.end","tags":{"job_name":"$1"}},{"match":"airflow.*_heartbeat_failure","name":"airflow.job.heartbeat.failure","tags":{"job_name":"$1"}},{"match":"airflow.operator_failures_*","name":"airflow.operator_failures","tags":{"operator_name":"$1"}},{"match":"airflow.operator_successes_*","name":"airflow.operator_successes","tags":{"operator_name":"$1"}},{"match":"airflow\\.dag_processing\\.last_runtime\\.(.*)","match_type":"regex","name":"airflow.dag_processing.last_runtime","tags":{"dag_file":"$1"}},{"match":"airflow\\.dag_processing\\.last_run\\.seconds_ago\\.(.*)","match_type":"regex","name":"airflow.dag_processing.last_run.seconds_ago","tags":{"dag_file":"$1"}},{"match":"airflow\\.dag\\.loading-duration\\.(.*)","match_type":"regex","name":"airflow.dag.loading_duration","tags":{"dag_file":"$1"}},{"match":"airflow.dagrun.*.first_task_scheduling_delay","name":"airflow.dagrun.first_task_scheduling_delay","tags":{"dag_id":"$1"}},{"match":"airflow.pool.open_slots.*","name":"airflow.pool.open_slots","tags":{"pool_name":"$1"}},{"match":"airflow.pool.queued_slots.*","name":"airflow.pool.queued_slots","tags":{"pool_name":"$1"}},{"match":"airflow.pool.running_slots.*","name":"airflow.pool.running_slots","tags":{"pool_name":"$1"}},{"match":"airflow.pool.used_slots.*","name":"airflow.pool.used_slots","tags":{"pool_name":"$1"}},{"match":"airflow.pool.starving_tasks.*","name":"airflow.pool.starving_tasks","tags":{"pool_name":"$1"}},{"match":"airflow\\.dagrun\\.dependency-check\\.(.*)","match_type":"regex","name":"airflow.dagrun.dependency_check","tags":{"dag_id":"$1"}},{"match":"airflow\\.dag\\.(.*)\\.([^.]*)\\.duration","match_type":"regex","name":"airflow.dag.task.duration","tags":{"dag_id":"$1","task_id":"$2"}},{"match":"airflow\\.dag_processing\\.last_duration\\.(.*)","match_type":"regex","name":"airflow.dag_processing.last_duration","tags":{"dag_file":"$1"}},{"match":"airflow\\.dagrun\\.duration\\.success\\.(.*)","match_type":"regex","name":"airflow.dagrun.duration.success","tags":{"dag_id":"$1"}},{"match":"airflow\\.dagrun\\.duration\\.failed\\.(.*)","match_type":"regex","name":"airflow.dagrun.duration.failed","tags":{"dag_id":"$1"}},{"match":"airflow\\.dagrun\\.schedule_delay\\.(.*)","match_type":"regex","name":"airflow.dagrun.schedule_delay","tags":{"dag_id":"$1"}},{"match":"airflow.scheduler.tasks.running","name":"airflow.scheduler.tasks.running"},{"match":"airflow.scheduler.tasks.starving","name":"airflow.scheduler.tasks.starving"},{"match":"airflow.sla_email_notification_failure","name":"airflow.sla_email_notification_failure"},{"match":"airflow\\.task_removed_from_dag\\.(.*)","match_type":"regex","name":"airflow.dag.task_removed","tags":{"dag_id":"$1"}},{"match":"airflow\\.task_restored_to_dag\\.(.*)","match_type":"regex","name":"airflow.dag.task_restored","tags":{"dag_id":"$1"}},{"match":"airflow.task_instance_created-*","name":"airflow.task.instance_created","tags":{"task_class":"$1"}},{"match":"airflow\\.ti\\.start\\.(.+)\\.(\\w+)","match_type":"regex","name":"airflow.ti.start","tags":{"dag_id":"$1","task_id":"$2"}},{"match":"airflow\\.ti\\.finish\\.(\\w+)\\.(.+)\\.(\\w+)","name":"airflow.ti.finish","match_type":"regex","tags":{"dag_id":"$1","task_id":"$2","state":"$3"}}]}]
  ```

##### Log collection

_Available for Agent versions >6.0_

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes Log Collection][14].

| Parameter      | Value                                                 |
|----------------|-------------------------------------------------------|
| `<LOG_CONFIG>` | `{"source": "airflow", "service": "<YOUR_APP_NAME>"}` |

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's status subcommand][15] and look for `airflow` under the Checks section.

## Annexe

### Airflow DatadogHook

In addition, [Airflow DatadogHook][16] can be used to interact with Datadog:

- Send Metric
- Query Metric
- Post Event

## Data Collected

### Metrics

See [metadata.csv][17] for a list of metrics provided by this check.

### Events

The Airflow check does not include any events.

### Service Checks

See [service_checks.json][18] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][11].


[1]: https://airflow.apache.org/docs/stable/metrics.html
[2]: https://docs.datadoghq.com/developers/dogstatsd/
[3]: https://docs.datadoghq.com/agent/
[4]: https://app.datadoghq.com/account/settings/agent/latest
[5]: https://github.com/DataDog/integrations-core/blob/master/airflow/datadog_checks/airflow/data/conf.yaml.example
[6]: https://airflow.apache.org/docs/apache-airflow/stable/logging-monitoring/metrics.html
[7]: https://airflow.apache.org/docs/apache-airflow/stable/configurations-ref.html#metrics
[8]: https://docs.datadoghq.com/getting_started/agent/autodiscovery/?tab=docker#integration-templates
[9]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/
[10]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[11]: https://docs.datadoghq.com/help/
[12]: https://docs.datadoghq.com/developers/dogstatsd/?tab=kubernetes#setup
[13]: /integrations/airflow/?tab=host#connect-airflow-to-dogstatsd
[14]: https://docs.datadoghq.com/agent/kubernetes/integrations/?tab=kubernetes#configuration
[15]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[16]: https://airflow.apache.org/docs/apache-airflow-providers-datadog/stable/_modules/airflow/providers/datadog/hooks/datadog.html
[17]: https://github.com/DataDog/integrations-core/blob/master/airflow/metadata.csv
[18]: https://github.com/DataDog/integrations-core/blob/master/airflow/assets/service_checks.json
[19]: https://airflow.apache.org/docs/apache-airflow/stable/configurations-ref.html#base-url
[20]: https://airflow.apache.org/docs/apache-airflow/stable/executor/kubernetes.html
