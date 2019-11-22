# Agent Check: Airflow

## Overview

This check monitors [Airflow][1] through the Datadog Agent.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying these instructions.

### Installation

The Airflow check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `airflow.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your airflow performance data. See the [sample airflow.d/conf.yaml][3] for all available configuration options.

2. [Restart the Agent][4].

### Validation

[Run the Agent's status subcommand][5] and look for `airflow` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][6] for a list of metrics provided by this check.

### Service Checks

Airflow does not include any service checks.

### Events

Airflow does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][7].

[1]: **LINK_TO_INTEGRATION_SITE**
[2]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[3]: https://github.com/DataDog/integrations-core/blob/master/airflow/datadog_checks/airflow/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/airflow/metadata.csv
[7]: https://docs.datadoghq.com/help


















# NOTES

```
docker run -v /home/vagrant/airflow.cfg:/usr/local/airflow/airflow.cfg -p 8080:8080 my-airflow webserver


Airflow.cfg
# Statsd (https://github.com/etsy/statsd) integration settings
statsd_on = True
statsd_host = localhost
statsd_port = 8125
statsd_prefix = airflow

```

```yaml
dogstatsd_mapper_cache_size: 500
dogstatsd_mappings:
  - match: 'airflow.*_start'
    name: 'airflow.job.start'
    tags:
      job_name: '$1'
  - match: 'airflow.*_end'
    name: 'airflow.job.end'
    tags:
      job_name: '$1'
  - match: 'airflow.operator_failures_*'
    name: 'airflow.operator_failures'
    tags:
      operator_name: '$1'
  - match: 'airflow.operator_successes_*'
    name: 'airflow.operator_successes'
    tags:
      operator_name: '$1'
  - match: 'airflow\.dag_processing\.last_runtime\.(.*)'
    match_type: 'regex'
    name: 'airflow.dag_processing.last_runtime'
    tags:
       dag_file: '$1'
  - match: 'airflow\.dag_processing\.last_run\.seconds_ago\.(.*)'
    match_type: 'regex'
    name: 'airflow.dag_processing.last_run'
    tags:
       dag_file: '$1'
  - match: 'airflow\.dag\.loading-duration\.(.*)'
    match_type: 'regex'
    name: 'airflow.dag.loading_duration'
    tags:
       dag_file: '$1'
  - match: 'airflow.pool.open_slots.*'
    name: 'airflow.pool.open_slots'
    tags:
       pool_name: '$1'
  - match: 'airflow.pool.used_slots.*'
    name: 'airflow.pool.used_slots'
    tags:
       pool_name: '$1'
  - match: 'airflow.pool.starving_tasks.*'
    name: 'airflow.pool.starving_tasks'
    tags:
       pool_name: '$1'
  - match: 'airflow.dagrun.dependency-check.*'
    name: 'airflow.dagrun.dependency_check'
    tags:
       dag_id: '$1'
  - match: 'airflow.dag.*.*.duration'
    name: 'airflow.dag.duration'
    tags:
       dag_id: '$1'
       task_id: '$2'
  - match: 'airflow\.dag_processing\.last_duration\.(.*)'
    match_type: 'regex'
    name: 'airflow.dag_processing.last_duration'
    tags:
       dag_file: '$1'
  - match: 'airflow.dagrun.duration.success.*'
    name: 'airflow.dagrun.duration.success'
    tags:
       dag_id: '$1'
  - match: 'airflow.dagrun.duration.failed.*'
    name: 'airflow.dagrun.duration.failed'
    tags:
       dag_id: '$1'
  - match: 'airflow.dagrun.schedule_delay.*'
    name: 'airflow.dagrun.schedule_delay'
    tags:
       dag_id: '$1'
```
