# Agent Check: n8n

## Overview

This check monitors [n8n][1] through the Datadog Agent.

Collect n8n metrics including:
- Cache metrics: hit, miss, and update counts.
- Workflow metrics: started, success, failed counters, audit workflow lifecycle counters; in n8n 2.x, an execution-duration histogram.
- Node metrics: per-node started and finished counters emitted by worker processes in queue mode.
- Queue metrics: queue depth, enqueued/dequeued/completed/failed/stalled counters, and scaling-mode worker gauges.
- HTTP metrics: request duration histograms tagged with status code.
- Process and Node.js runtime metrics.


## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The n8n check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

#### Enable the n8n metrics endpoint

The `/metrics` endpoint is disabled by default and must be enabled in your n8n configuration. Note that the `/metrics` endpoint is only available for self-hosted instances and is not available on n8n Cloud.

Set the following environment variables to enable metrics:

```bash
# Required: Enable the metrics endpoint
N8N_METRICS=true

# Optional: Include additional metric categories
N8N_METRICS_INCLUDE_DEFAULT_METRICS=true
N8N_METRICS_INCLUDE_CACHE_METRICS=true
N8N_METRICS_INCLUDE_MESSAGE_EVENT_BUS_METRICS=true
N8N_METRICS_INCLUDE_WORKFLOW_ID_LABEL=true
N8N_METRICS_INCLUDE_API_ENDPOINTS=true
N8N_METRICS_INCLUDE_QUEUE_METRICS=true

# Optional: n8n 2.x adds workflow_statistics gauges (workflows, users, executions, ...) - opt in
N8N_METRICS_INCLUDE_WORKFLOW_STATISTICS=true

# Optional: Customize the metric prefix (default is 'n8n_')
N8N_METRICS_PREFIX=n8n_
```

For more details, see the n8n documentation on [enabling Prometheus metrics][10].

If you change `N8N_METRICS_PREFIX` from its default of `n8n_`, you **must** also set `raw_metric_prefix` in the integration's `conf.yaml` to the same value. Otherwise the check will not recognize the exposed metric names and will silently submit nothing:

```yaml
instances:
  - openmetrics_endpoint: http://localhost:5678/metrics
    raw_metric_prefix: my_custom_prefix_
```

#### Event-driven counters

Some n8n counters are registered dynamically the first time the corresponding event fires. For example, `n8n.workflow.started.count`, `n8n.workflow.success.count`, `n8n.workflow.failed.count`, audit workflow lifecycle counters, and the queue and node event counters do not appear until the corresponding workflow or queue event has occurred. This is expected behavior and is not a sign of a misconfigured integration.

#### Queue mode and workers

In queue mode, n8n runs separate worker processes that execute jobs picked up from a Redis-backed queue. Each worker exposes its own `/metrics` endpoint and emits a different subset of metrics than the main process. Worker-observed metrics include `n8n.queue.job.dequeued.count`, `n8n.queue.job.stalled.count`, `n8n.node.started.count`, `n8n.node.finished.count`, and `n8n.runner.task.requested.count`. Main-only metrics include `n8n.instance.role.leader` and the `n8n.scaling.mode.queue.jobs.*` family.

To expose worker metrics, set `QUEUE_HEALTH_CHECK_ACTIVE=true` and `QUEUE_HEALTH_CHECK_PORT=<port>` on each worker. **In n8n 2.x, port `5679` is reserved for the task runner broker, so pick a different port (for example `5680`).**

For full coverage in queue deployments, configure one Datadog instance per n8n process exposing `/metrics`, including main and worker processes:

```yaml
instances:
  - openmetrics_endpoint: http://n8n-main:5678/metrics
  - openmetrics_endpoint: http://n8n-worker:5680/metrics
```

#### Version-specific metrics

Several metric families were introduced in n8n 2.x and are not emitted on n8n 1.x:

- `n8n.workflow.execution.duration.seconds.*` (histogram)
- `n8n.audit.workflow.activated.count`, `n8n.audit.workflow.deactivated.count`, `n8n.audit.workflow.executed.count`, `n8n.audit.workflow.resumed.count`, `n8n.audit.workflow.version.updated.count`, and `n8n.audit.workflow.waiting.count`
- `n8n.embed.login.requests.count` (tagged with `result:success`/`failure`), `n8n.embed.login.failures.count` (tagged with `reason`)
- `n8n.token.exchange.requests.count` (tagged with `result:success`/`failure`), `n8n.token.exchange.failures.count` (tagged with `reason`), `n8n.token.exchange.identity.linked.count`, `n8n.token.exchange.jit.provisioning.count`
- `n8n.process.pss.bytes` (Linux only)
- The `n8n.{production,manual,production.root}.executions`, `n8n.users.total`, `n8n.enabled.users`, `n8n.workflows.total`, and `n8n.credentials.total` family - only emitted when `N8N_METRICS_INCLUDE_WORKFLOW_STATISTICS=true` is set.

Some metrics only emit samples after the corresponding runtime event occurs. For example, failures-only counters (`*.failures.count`) need an authentication failure, audit workflow counters need the matching workflow state transition, and the libuv `n8n.nodejs.active.requests` gauge needs an in-flight libuv request. A healthy idle deployment may not produce data points for these metrics until that activity occurs.

#### Tag cardinality

When `N8N_METRICS_INCLUDE_WORKFLOW_ID_LABEL=true`, http and workflow execution histograms are tagged with `workflow_id` (and similar labels for nodes). On deployments with many distinct workflows or nodes, this can produce high-cardinality metrics. Drop the label via `exclude_labels` or omit `N8N_METRICS_INCLUDE_WORKFLOW_ID_LABEL` to keep tag cardinality bounded.

#### Configure the Datadog Agent

1. Edit the `n8n.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your n8n performance data. See the [sample n8n.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

### Log collection

_Available for Agent versions >6.0_

#### Enable n8n logging

Configure n8n to output logs by setting the following environment variables:

```bash
# Set the log level (error, warn, info, debug)
N8N_LOG_LEVEL=info

# Output logs to console (for containerized environments) or file
N8N_LOG_OUTPUT=console

# If using file output, specify the log file location
N8N_LOG_FILE_LOCATION=/var/log/n8n/n8n.log
```

#### Structured event logs

n8n can output structured JSON logs to `n8nEventLog.log` containing detailed workflow execution events. Enable this by setting the log output to file:

```bash
N8N_LOG_OUTPUT=file
N8N_LOG_FILE_LOCATION=/var/log/n8n/
```

The event log includes the following event types:

| Event Type | Description |
|------------|-------------|
| `n8n.workflow.started` | Workflow execution has begun |
| `n8n.workflow.success` | Workflow completed successfully |
| `n8n.workflow.failed` | Workflow execution failed |
| `n8n.node.started` | Individual node started execution |
| `n8n.node.finished` | Individual node completed execution |
| `n8n.audit.workflow.executed` | Audit trail for workflow execution |

Each event contains rich metadata including `executionId`, `workflowId`, `workflowName`, `nodeType`, `nodeName`, and timestamps for correlation with metrics.

#### Configure the Datadog Agent to collect logs

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

2. Add this configuration block to your `n8n.d/conf.yaml` file to start collecting your n8n logs:

   ```yaml
   logs:
     - type: file
       path: /var/log/n8n/*.log
       source: n8n
       service: n8n
   ```

   For containerized environments using Docker, use the following configuration instead:

   ```yaml
   logs:
     - type: docker
       source: n8n
       service: n8n
   ```

3. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `n8n` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The n8n integration does not include any events.

### Service Checks

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: https://n8n.io/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/containers/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/n8n/datadog_checks/n8n/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/configuration/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/configuration/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/n8n/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/n8n/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://docs.n8n.io/hosting/configuration/configuration-examples/prometheus/
