# Agent Check: Control-M

## Overview

This check monitors [Control-M][1] through the Datadog Agent.

Control-M is a workload automation platform that orchestrates batch jobs, file transfers, and application workflows across on-premises and cloud environments. This integration connects to the Control-M Automation API to collect server health, job execution metrics, and completion events, giving you visibility into your scheduling infrastructure from within Datadog.

The integration provides:

- **Server health monitoring** — track which Control-M servers are up or disconnected.
- **Job rollup metrics** — total, active, waiting, and per-status breakdowns across all servers.
- **Per-job completion tracking** — run counts and durations for terminal jobs (ended OK, ended not OK, cancelled), with deduplication across check cycles.
- **Events** — optional Datadog events for job failures, cancellations, slow runs, and (opt-in) successes.
- **Metadata** — Control-M server version reported to the Datadog Agent.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The Control-M check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

Edit the `control_m.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory.

#### Minimum configuration (static token)

```yaml
instances:
  - control_m_api_endpoint: https://your-controlm-host:8443/automation-api
    headers:
      Authorization: Bearer <YOUR_API_TOKEN>
```

#### Session-login authentication

If your environment uses username/password authentication instead of a static token:

```yaml
instances:
  - control_m_api_endpoint: https://your-controlm-host:8443/automation-api
    control_m_username: <USERNAME>
    control_m_password: <PASSWORD>
```

When both `headers` (with an `Authorization` key) and credentials are configured, the check tries the static token first. If the API responds with a 401, it falls back to session login automatically.

#### Optional settings

```yaml
instances:
  - control_m_api_endpoint: https://your-controlm-host:8443/automation-api
    headers:
      Authorization: Bearer <YOUR_API_TOKEN>

    # Events
    emit_job_events: true            # Emit Datadog events for job completions (default: false)
    emit_success_events: false       # Include success events, not just failures/cancellations (default: false)
    slow_run_threshold_ms: 3600000   # Flag jobs slower than this as slow_run events (default: none)

    # Job filtering
    job_status_limit: 10000          # Max jobs per API call (default: 10000, server max)
    job_name_filter: '*'             # Wildcard filter for job names (default: *)

    # Session token tuning
    token_lifetime_seconds: 1800     # Assumed token lifetime (default: 1800)
    token_refresh_buffer_seconds: 300  # Refresh this many seconds before expiry (default: 300)

    # Deduplication TTLs
    finalized_ttl_seconds: 86400     # How long to remember completed jobs (default: 24h)
    active_ttl_seconds: 21600        # How long to track active jobs (default: 6h)
```

See the [sample control_m.d/conf.yaml][4] for all available configuration options.

[Restart the Agent][5] after making changes.

### Validation

[Run the Agent's status subcommand][6] and look for `control_m` under the Checks section.

```
$ datadog-agent status
  ...
  control_m (1.0.0)
  -----------------
    Instance ID: control_m:abc1234 [OK]
    Configuration Source: file:/etc/datadog-agent/conf.d/control_m.d/conf.yaml
    Total Runs: 42
    Metric Samples: Last Run: 15, Total: 630
    Events: Last Run: 0, Total: 3
    Service Checks: Last Run: 1, Total: 42
    Average Execution Time: 245ms
```

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

#### Histogram: `control_m.job.run.duration_ms`

The `job.run.duration_ms` metric is submitted as a [histogram][9]. The Datadog Agent expands it into multiple aggregated metrics based on the [`histogram_aggregates`][10] and [`histogram_percentiles`][10] settings in the main `datadog.yaml`:

| Generated metric | Type | Default |
|---|---|---|
| `control_m.job.run.duration_ms.avg` | gauge | Enabled |
| `control_m.job.run.duration_ms.count` | rate | Enabled |
| `control_m.job.run.duration_ms.max` | gauge | Enabled |
| `control_m.job.run.duration_ms.median` | gauge | Enabled |
| `control_m.job.run.duration_ms.95percentile` | gauge | Enabled |

To customize which aggregations are produced, edit the `histogram_aggregates` and `histogram_percentiles` options in your `datadog.yaml`:

```yaml
histogram_aggregates:
  - max
  - median
  - avg
  - count

histogram_percentiles:
  - "0.95"
```

These settings are Agent-level and apply to all histograms from all integrations.

### Events

When `emit_job_events` is enabled, the check emits Datadog events for terminal job completions:

| Event type | Alert type | Trigger |
|---|---|---|
| `control_m.job.completion` | `error` | Job ended not OK. |
| `control_m.job.completion` | `warning` | Job cancelled. |
| `control_m.job.completion` | `success` | Job ended OK (only when `emit_success_events: true`). |
| `control_m.job.slow_run` | `warning` | Job duration exceeds `slow_run_threshold_ms`. |

Events include high-cardinality details in the body: job ID, run number, folder, type, start time, and duration.

Events respect deduplication — the same job+run combination only fires an event on the first check cycle it appears.

## Troubleshooting

### The `can_connect` metric reports 0

- Verify the `control_m_api_endpoint` is reachable from the Agent host: `curl -s -o /dev/null -w '%{http_code}' https://your-host:8443/automation-api/config/servers -H 'Authorization: Bearer <TOKEN>'`
- Check that the API token or credentials are valid.
- If TLS verification is failing, set `tls_verify: false` temporarily to confirm, then fix the certificate chain.

### Metrics show fewer jobs than expected

- The API has a server-enforced maximum of 10,000 jobs per request. If `jobs.total` exceeds `jobs.returned`, some jobs are being truncated. Consider using `job_name_filter` to narrow the scope.

### Events are not appearing

- Verify `emit_job_events: true` is set in the instance configuration.
- Success events require both `emit_job_events: true` and `emit_success_events: true`.
- Events respect deduplication — a job that was already reported in a previous check cycle will not fire again.

### Duplicate metrics after Agent restart

- The check persists dedup state to the Agent's cache. If the cache was cleared (e.g., a clean reinstall), previously reported terminal jobs may be re-emitted once. Increase `finalized_ttl_seconds` if completed jobs remain visible in the Control-M status feed for longer than 24 hours.

Need help? Contact [Datadog support][8].


[1]: https://www.bmc.com/it-solutions/control-m.html
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/containers/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/control_m/datadog_checks/control_m/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/configuration/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/configuration/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/control_m/metadata.csv
[8]: https://docs.datadoghq.com/help/
[9]: https://docs.datadoghq.com/metrics/types/?tab=histogram
[10]: [https://github.com/DataDog/datadog-agent/blob/main/pkg/config/config_template.yaml#L210-L227](https://github.com/DataDog/datadog-agent/blob/3697d3b93bde62e2c3bf039e170ce69e49ef5294/pkg/config/config_template.yaml#L225-L242)
