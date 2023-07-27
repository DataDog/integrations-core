# Agent Check: Airbyte

## Overview

This check monitors [Airbyte][1]. Metrics are sent to Datadog via [DogStatsD][2].

## Setup

### Installation

All steps below are needed for the Airflow integration to work properly. Before you begin, [install the Datadog Agent][3] version `>=6.17` or `>=7.17`, which includes the StatsD/DogStatsD mapping feature.

### Configuration

1. Configure your Airbyte deployment [to send metrics to Datadog][6]
2. Update the [Datadog Agent main configuration file][7] `datadog.yaml` by adding the following configuration:

```yaml
   dogstatsd_mapper_profiles:
     - name: airbyte
       prefix: "airbyte."
       mappings:
         - match: "temporal_workflow_*"
           name: "airbyte.temporal_workflow.$1"
         - match: "state_commit_*"
           name: "airbyte.state_commit.$1"
         - match: "job_*"
           name: "airbyte.job.$1"
         - match: "activity_*"
           name: "airbyte.activity.$1"
         - match: "attempt_*"
           name: "airbyte.attempt.$1"
         - match: "cron_*"
           name: "airbyte.$1"
         - match: "worker_*"
           name: "airbyte.$1"
         - match: "*"
           name: "airbyte.$1"
```
3. [Restart the Agent][5] and Airbyte.

## Data Collected

### Metrics

See [metadata.csv][8] for a list of metrics provided by this check.

### Service Checks

Airbyte does not include any service checks.

### Events

Airbyte does not include any events.

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
