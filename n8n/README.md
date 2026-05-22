# Agent Check: n8n

## Overview

This check monitors [n8n][1] through the Datadog Agent.

This integration collects n8n metrics including:
- Cache metrics: hit, miss, and update counts.
- Workflow metrics: started, success, and failed counters. Audit workflow life cycle counters. In n8n 2.x, an execution-duration histogram.
- Node metrics: per-node counters (started and finished) emitted by worker processes in queue mode.
- Queue metrics: queue depth; enqueued, dequeued, completed, failed, and stalled counters; and scaling-mode worker gauges.
- HTTP metrics: request duration histograms tagged with status code.
- Process and Node.js runtime metrics.


## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery integration templates][3] for guidance on applying these instructions.

### Installation

The n8n check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

#### Enable the n8n metrics endpoint

The `/metrics` endpoint is disabled by default and must be enabled in your n8n configuration. **Note**: The `/metrics` endpoint is only available for self-hosted instances and is not available on n8n Cloud.

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

If you change `N8N_METRICS_PREFIX` from its default of `n8n_`, you **must** also set `raw_metric_prefix` in the integration's `conf.yaml` to the same value. Otherwise the check does not recognize the exposed metric names and silently submits nothing:

```yaml
instances:
  - openmetrics_endpoint: http://localhost:5678/metrics
    raw_metric_prefix: my_custom_prefix_
```

#### Event-driven counters

Most n8n counters are registered dynamically the first time their underlying event fires. The integration ships mappings for around 70 of these event-bus counters, including:

- Workflow life cycle: `n8n.workflow.started.count`, `n8n.workflow.success.count`, `n8n.workflow.failed.count`, `n8n.workflow.cancelled.count`
- Audit (workflow, user, credentials, package, variable, execution data): `n8n.audit.workflow.executed.count`, `n8n.audit.user.login.success.count`, `n8n.audit.user.credentials.created.count`, and similar
- AI nodes: `n8n.ai.tool.called.count`, `n8n.ai.llm.generated.count`, `n8n.ai.vector.store.searched.count`, and similar
- Runner, queue, and node life cycle: `n8n.runner.task.requested.count`, `n8n.queue.job.completed.count`, `n8n.node.started.count`, `n8n.node.finished.count`

These counters do not appear on the `/metrics` endpoint until the corresponding event has occurred. A healthy idle deployment does not produce datapoints for them until that activity fires. The complete list is in [`metadata.csv`][7].

If a future n8n release exposes a new event-driven counter that is not yet covered by this integration, add it to the `extra_metrics` option in your instance configuration:

```yaml
instances:
  - openmetrics_endpoint: http://n8n:5678/metrics
    extra_metrics:
      - some_new_n8n_event_total: some.new.n8n.event
```

The left-hand side is the Prometheus counter name as n8n exposes it (keep the `_total` suffix). The right-hand side is the dotted Datadog metric name to submit it as.

#### Queue mode and workers

In queue mode, n8n runs separate worker processes that execute jobs picked up from a Redis-backed queue. Each worker exposes its own `/metrics` endpoint and emits a different subset of metrics than the main process. Worker-observed metrics include `n8n.queue.job.dequeued.count`, `n8n.queue.job.stalled.count`, `n8n.node.started.count`, `n8n.node.finished.count`, and `n8n.runner.task.requested.count`. Main-only metrics include `n8n.instance.role.leader` and the `n8n.scaling.mode.queue.jobs.*` family.

To expose worker metrics, set `QUEUE_HEALTH_CHECK_ACTIVE=true` and `QUEUE_HEALTH_CHECK_PORT=<port>` on each worker.

**Note**: In n8n 2.x, port `5679` is reserved for the task runner broker. Pick a different port (for example `5680`).

For full coverage in queue deployments, configure one Datadog instance per n8n process exposing `/metrics`, including main and worker processes:

```yaml
instances:
  - openmetrics_endpoint: http://n8n-main:5678/metrics
  - openmetrics_endpoint: http://n8n-worker:5680/metrics
```

#### Version-specific metrics

Several metric families were introduced in n8n 2.x and are not emitted on n8n 1.x:

- `n8n.workflow.execution.duration.seconds.*` (histogram). Gated by `N8N_METRICS_INCLUDE_WORKFLOW_EXECUTION_DURATION`, which defaults to `true` in n8n 2.x.
- `n8n.audit.workflow.activated.count`, `n8n.audit.workflow.deactivated.count`, `n8n.audit.workflow.executed.count`, `n8n.audit.workflow.resumed.count`, `n8n.audit.workflow.version.updated.count`, and `n8n.audit.workflow.waiting.count`
- `n8n.embed.login.requests.count` (tagged with `result:success` or `result:failure`), `n8n.embed.login.failures.count` (tagged with `reason`)
- `n8n.token.exchange.requests.count` (tagged with `result:success` or `result:failure`), `n8n.token.exchange.failures.count` (tagged with `reason`), `n8n.token.exchange.identity.linked.count`, `n8n.token.exchange.jit.provisioning.count`
- `n8n.process.pss.bytes` (Linux only)
- The `n8n.{production,manual,production.root}.executions`, `n8n.users.total`, `n8n.enabled.users`, `n8n.workflows.total`, and `n8n.credentials.total` family. Only emitted when `N8N_METRICS_INCLUDE_WORKFLOW_STATISTICS=true` is set.
- The `n8n.expression.*` family (`evaluation.duration.seconds`, `code.cache.{hit,miss,eviction,size}`, `pool.{acquired,replenish.failed,scaled.up,scaled.to.zero}`). Only emitted when n8n is running the new VM-isolated expression engine *and* observability for it is on. Set `N8N_EXPRESSION_ENGINE=vm` and `N8N_EXPRESSION_ENGINE_OBSERVABILITY_ENABLED=true` on the n8n process; both default to off (the engine defaults to `legacy`). These metrics surface the per-expression evaluation latency, the compiled-expression LRU cache hit and miss rates, and the V8-isolate pool's idle scaling behavior. They are most useful for troubleshooting workflow latency that traces back to slow `{{ ... }}` evaluation.

Some metrics only emit samples after the corresponding runtime event occurs. For example, failures-only counters (`*.failures.count`) need an authentication failure, audit workflow counters need the matching workflow state transition, and the libuv `n8n.nodejs.active.requests` gauge needs an in-flight libuv request. A healthy idle deployment may not produce datapoints for these metrics until that activity occurs.

#### Tag cardinality

When `N8N_METRICS_INCLUDE_WORKFLOW_ID_LABEL=true`, http and workflow execution histograms are tagged with `workflow_id` (and similar labels for nodes). On deployments with many distinct workflows or nodes, this can produce high-cardinality metrics. Drop the label through `exclude_labels` or omit `N8N_METRICS_INCLUDE_WORKFLOW_ID_LABEL` to keep tag cardinality bounded.

#### Configure the Datadog Agent

1. Edit the `n8n.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your n8n performance data. See the [sample n8n.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

### Log collection

**Note**: Available for Agent versions 6.0 and later.

#### Enable n8n logging

Configure n8n application logs by setting the following environment variables:

```bash
# Set the log level (error, warn, info, debug)
N8N_LOG_LEVEL=info

# Output application logs to console or file
N8N_LOG_OUTPUT=console

# Use JSON formatting so Datadog can parse n8n application log attributes
N8N_LOG_FORMAT=json

# If using file output, specify the application log file location
N8N_LOG_FILE_LOCATION=/var/log/n8n/n8n.log
```

#### Structured event logs

n8n also writes structured event bus logs to `n8nEventLog*.log`. These logs contain workflow, node, queue, runner, and audit events and are separate from the application logs controlled by `N8N_LOG_OUTPUT` and `N8N_LOG_FILE_LOCATION`.

By default, event bus log files are written under the n8n user folder, for example:

- Host installations: `~/.n8n/n8nEventLog*.log`
- Official Docker image: `/home/node/.n8n/n8nEventLog*.log`

If you use a custom n8n user folder, collect the event bus logs from that folder instead. If you customize the event bus log file base name with `N8N_EVENTBUS_LOGWRITER_LOGBASENAME`, update the Datadog log path to match.

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

2. Add log collection entries to your `n8n.d/conf.yaml` file.

   For a host-based n8n installation where the Agent can read local files, collect the application log file and the event bus log files:

   ```yaml
   logs:
     - type: file
       path: /var/log/n8n/*.log
       source: n8n
       service: <SERVICE>
     - type: file
       path: /home/n8n/.n8n/n8nEventLog*.log
       source: n8n
       service: <SERVICE>
   ```

   Adjust `/home/n8n/.n8n/n8nEventLog*.log` to the n8n user folder on your host.

   For a containerized n8n deployment, collect stdout and stderr from the n8n container for application logs, and make the n8n user folder available to the Agent for event bus file logs. For example, if the n8n data directory is mounted on the host at `/var/lib/n8n`, configure:

   ```yaml
   logs:
     - type: docker
       source: n8n
       service: <SERVICE>
     - type: file
       path: /var/lib/n8n/n8nEventLog*.log
       source: n8n
       service: <SERVICE>
   ```

   If the Agent runs in a container, mount the n8n data volume or host directory into the Agent container and use the path as seen from inside the Agent container.

3. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `n8n` under the Checks section.

## Data collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The n8n integration does not include any events.

### Service checks

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
