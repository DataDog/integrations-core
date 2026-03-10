# Agent Check: Prefect

## Overview

This check monitors [Prefect Server][1] through the Datadog Agent.

Prefect is a Python-first workflow orchestration platform used to schedule and execute flows and tasks across work pools, work queues, and workers. This integration collects orchestration health and performance metrics and events directly from the [Prefect Server API][2] and supports [log collection][3] for comprehensive monitoring.

### What this integration monitors

The integration collects metrics across multiple layers of the Prefect orchestration hierarchy:

-   **Server Health**: API readiness and health status to confirm the control plane is operational.
-   **Work Pool Layer**: Pool readiness, paused/not-ready state, and aggregated worker availability to detect capacity or configuration issues.
-   **Worker Layer**: Online/offline status and heartbeat age to identify lost or unhealthy workers.
-   **Work Queue Layer**: Backlog size, backlog age, last polled age, concurrency utilization, and queue state (ready/paused/not-ready) to detect congestion, starvation, and stalled consumers.
-   **Deployment & Flow Layer**: Flow run counts by state (running, completed, failed, crashed, etc.), throughput, late starts, execution duration, queue wait time, and retry gaps to track reliability and latency percentiles.
-   **Task Layer**: Task run counts by state, throughput, execution duration, and dependency wait time to enable drilldowns from slow flows to individual task bottlenecks.
-   **Events**: Prefect events for state transitions and lifecycle changes.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][4] for guidance on applying these instructions.

### Installation

The Prefect check is included in the [Datadog Agent][5] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `prefect.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your Prefect performance data. See the [sample prefect.d/conf.yaml][6] for all available configuration options.

2. [Restart the Agent][7].

### Validation

[Run the Agent's status subcommand][8] and look for `prefect` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][9] for a list of metrics provided by this integration.

### Logs 
1. Enable log collection in your `datadog.yaml` file:

```
logs_enabled: true
```
2. Uncomment and edit the logs configuration block in your `prefect.d/conf.yaml` file. For example:
```
logs:
  - type: docker
    source: prefect
    service: <SERVICE>
```

### Events

The Prefect integration includes event support. Events are disabled by default; to enable them, set `collect_events` to `true` in the configuration.

Once enabled, the integration submits flow-run, task-run, and ready/not-ready events. The set of submitted events can be customized by adding or removing entries in the configuration.

### Service Checks

The Prefect integration does not include any service checks.


## Troubleshooting

Need help? Contact [Datadog support][10].


[1]: https://www.prefect.io/
[2]: https://docs.prefect.io/v3/api-ref/rest-api/server/index
[3]: https://docs.datadoghq.com/logs/log_collection/
[4]: https://docs.datadoghq.com/containers/kubernetes/integrations/
[5]: https://app.datadoghq.com/account/settings/agent/latest
[6]: https://github.com/DataDog/integrations-core/blob/master/prefect/datadog_checks/prefect/data/conf.yaml.example
[7]: https://docs.datadoghq.com/agent/configuration/agent-commands/#start-stop-and-restart-the-agent
[8]: https://docs.datadoghq.com/agent/configuration/agent-commands/#agent-status-and-information
[9]: https://github.com/DataDog/integrations-core/blob/master/prefect/metadata.csv
[10]: https://docs.datadoghq.com/help/
