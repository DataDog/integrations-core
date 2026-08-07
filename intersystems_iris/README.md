# Agent Check: InterSystems IRIS

## Overview

This check monitors [InterSystems IRIS][1] through the Datadog Agent.

InterSystems IRIS is a data platform combining a high-performance database, interoperability engine, and analytics. This integration scrapes the built-in `/api/monitor/metrics` OpenMetrics endpoint that IRIS exposes, giving you visibility into instance health without any agent-side plugins or SQL queries.

The check collects instance telemetry across CPU and cache efficiency, licensing, journaling, the write daemon, the work queue manager, SQL activity, databases and disk usage, shared memory, locks, ECP (Enterprise Cache Protocol), the Web Gateway/CSP, mirroring, overall system status, and, when a production is running with SAM statistics enabled, interoperability metrics.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery integration templates][3] for guidance on applying these instructions.

### Installation

The IRIS check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

IRIS exposes Prometheus/OpenMetrics telemetry at `/api/monitor/metrics` on the instance's web server port (`52773` by default). This endpoint is unauthenticated by default; if you have secured it, use the `auth_token`, `username`/`password`, or `headers` options.

1. Edit the `intersystems_iris.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your IRIS performance data. See the [sample intersystems_iris.d/conf.yaml][4] for all available configuration options.

   ```yaml
   instances:
     - openmetrics_endpoint: http://%%host%%:52773/api/monitor/metrics
   ```

2. [Restart the Agent][5].

#### Interoperability metrics

The interoperability metrics (`intersystems_iris.interop.*`) are **not emitted by default**, even when a production is running. IRIS only records them when the SAM (System Alerting and Monitoring) interoperability sensors are enabled. To collect them, in each interoperability-enabled namespace:

1. Enable the **Record Statistics for SAM** setting. This is the per-namespace `^Ens.Config("Stats","RecordSAM")` flag, settable from the Management Portal (**Interoperability > Configure > Production Settings**) or with ObjectScript:

   ```objectscript
   Set ^Ens.Config("Stats","RecordSAM") = 1
   ```

2. Ensure a production is running in that namespace. Restart the production after enabling the setting so the sensors begin sampling.

Once both conditions hold, metrics such as `intersystems_iris.interop.hosts`, `.messages`, `.messages.per_sec`, `.queued`, and `.last_activity` appear on the standard `/api/monitor/metrics` endpoint and are collected automatically. They carry `namespace`, `production`, `interop_host`, and `status` tags. (The business-host name is submitted under `interop_host` rather than `host` to avoid colliding with the reporting infrastructure hostname.)

#### Interoperability interface counts (optional)

IRIS also exposes an always-on interface-count family (active/inbound/outbound/web-API interface counts) on a separate endpoint, `/api/monitor/interop/interfaces`. These are not collected by the default configuration. To gather them, add a second instance pointing at that endpoint:

```yaml
instances:
  - openmetrics_endpoint: http://%%host%%:52773/api/monitor/metrics
  - openmetrics_endpoint: http://%%host%%:52773/api/monitor/interop/interfaces
```

#### Conditional metric families

Several families only report when the corresponding subsystem is active, and are otherwise absent (this is expected, not an error):

- **Mirroring** (`intersystems_iris.mirror.*`): only on instances that are members of a mirror. Backup-only latency metrics report only while the backup is dejournaling.
- **ECP** (`intersystems_iris.ecp.*`, `.ecps.*`): only when the instance participates in an ECP application-server/data-server relationship with active remote traffic.
- **SQL active queries** (`intersystems_iris.sql.active_queries*`): reflect queries in flight at scrape time.

### Validation

[Run the Agent's status subcommand][6] and look for `intersystems_iris` under the Checks section.

### Log collection

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

2. Add the InterSystems IRIS `messages.log` file to your log collection by editing the `logs` block in `intersystems_iris.d/conf.yaml`:

   ```yaml
   logs:
     - type: file
       path: /usr/irissys/mgr/messages.log
       source: intersystems_iris
       service: <SERVICE>
       log_processing_rules:
         - type: multi_line
           name: new_log_start_with_date
           pattern: \d{2}/\d{2}/\d{2}-\d{2}:\d{2}:\d{2}
   ```

   Change the `path` value to match your instance's installation directory. For example, IRIS for Health typically uses `/opt/irishealth/mgr/messages.log`.

3. Restart the Agent.

**Note**: InterSystems IRIS writes `messages.log` timestamps in the instance's local time with no timezone offset. The log pipeline interprets these timestamps as UTC. If your IRIS instance does not run in UTC, collected log timestamps are shifted by the instance's UTC offset. Run your IRIS instance in UTC to keep log timestamps accurate.

## Data collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The InterSystems IRIS integration does not include any events.

### Service checks

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].

[1]: https://www.intersystems.com/products/intersystems-iris/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/containers/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/intersystems_iris/datadog_checks/intersystems_iris/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/configuration/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/configuration/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/intersystems_iris/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/intersystems_iris/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
