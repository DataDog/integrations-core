# Agent Check: Airbyte

## Overview

This check monitors [Airbyte][1]. Metrics are sent to Datadog through [DogStatsD][2].

## Setup

### Installation

All steps below are needed for the Airbyte integration to work properly. Before you begin, [install the Datadog Agent][3] version `>=6.17` or `>=7.17`, which includes the StatsD/DogStatsD mapping feature.

### Configuration

1. Configure your Airbyte deployment [to send metrics to Datadog][6].
2. Update the [Datadog Agent main configuration file][7] `datadog.yaml` by adding the following configuration:

```yaml
dogstatsd_mapper_profiles:
  - name: airbyte_worker
    prefix: "worker."
    mappings:
      - match: "worker.temporal_workflow_*"
        name: "airbyte.worker.temporal_workflow.$1"
      - match: "worker.worker_*"
        name: "airbyte.worker.$1"
      - match: "worker.state_commit_*"
        name: "airbyte.worker.state_commit.$1"
      - match: "worker.job_*"
        name: "airbyte.worker.job.$1"
      - match: "worker.attempt_*"
        name: "airbyte.worker.attempt.$1"
      - match: "worker.activity_*"
        name: "airbyte.worker.activity.$1"
      - match: "worker.*"
        name: "airbyte.worker.$1"
  - name: airbyte_cron
    prefix: "cron."
    mappings:
      - match: "cron.cron_jobs_run"
        name: "airbyte.cron.jobs_run"
      - match: "cron.*"
        name: "airbyte.cron.$1"
  - name: airbyte_metrics_reporter
    prefix: "metrics-reporter."
    mappings:
      - match: "metrics-reporter.*"
        name: "airbyte.metrics_reporter.$1"
  - name: airbyte_orchestrator
    prefix: "orchestrator."
    mappings:
      - match: "orchestrator.*"
        name: "airbyte.orchestrator.$1"
  - name: airbyte_server
    prefix: "server."
    mappings:
      - match: "server.*"
        name: "airbyte.server.$1"
  - name: airbyte_general
    prefix: "airbyte."
    mappings:
      - match: "airbyte.worker.temporal_workflow_*"
        name: "airbyte.worker.temporal_workflow.$1"
      - match: "airbyte.worker.worker_*"
        name: "airbyte.worker.$1"
      - match: "airbyte.worker.state_commit_*"
        name: "airbyte.worker.state_commit.$1"
      - match: "airbyte.worker.job_*"
        name: "airbyte.worker.job.$1"
      - match: "airbyte.worker.attempt_*"
        name: "airbyte.worker.attempt.$1"
      - match: "airbyte.worker.activity_*"
        name: "airbyte.worker.activity.$1"
      - match: "airbyte.cron.cron_jobs_run"
        name: "airbyte.cron.jobs_run"
```

3. [Restart the Agent][5] and Airbyte.

## Data Collected

### Metrics

See [metadata.csv][8] for a list of metrics provided by this check.

### Service Checks

The Airbyte check does not include any service checks.

### Events

The Airbyte check does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][4].

[1]: https://airbyte.com/
[2]: https://docs.datadoghq.com/developers/dogstatsd
[3]: https://app.datadoghq.com/account/settings/agent/latest
[4]: https://docs.datadoghq.com/help/
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[6]: https://docs.airbyte.com/operator-guides/collecting-metrics/
[7]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/
[8]: https://github.com/DataDog/integrations-core/blob/master/airbyte/metadata.csv
