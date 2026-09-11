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

Once both conditions hold, metrics such as `intersystems_iris.interop.hosts`, `.messages.count`, `.messages.per_sec.count`, `.queued`, and `.last_activity` appear on the standard `/api/monitor/metrics` endpoint and are collected automatically. They carry `namespace`, `production`, `interop_host`, and `status` tags. (The business-host name is submitted under `interop_host` rather than `host` to avoid colliding with the reporting infrastructure hostname.)

#### Conditional metric families

Several families only report when the corresponding subsystem is active, and are otherwise absent (this is expected, not an error):

- **Mirroring** (`intersystems_iris.mirror.*`): only on instances that are members of a mirror. Backup-only latency metrics report only while the backup is dejournaling.
- **ECP** (`intersystems_iris.ecp.*`, `.ecps.*`): only when the instance participates in an ECP application-server/data-server relationship with active remote traffic.
- **SQL active queries** (`intersystems_iris.sql.active_queries*`): reflect queries in flight at scrape time.

### Validation

[Run the Agent's status subcommand][6] and look for `intersystems_iris` under the Checks section.

### Log collection

IRIS can expose its log in two forms. [Structured logging][10] is recommended: the IRIS log daemon writes one JSON object per line, which Datadog parses without a multi-line rule, and it carries audit events and discrete named fields that `messages.log` only renders as prose. Collecting `messages.log` directly is still supported and is covered below.

Either way, collecting logs is disabled by default in the Datadog Agent. Enable it in your `datadog.yaml` file:

```yaml
logs_enabled: true
```

#### Structured logging

1. Configure the IRIS log daemon. In the Management Portal, go to **System Administration** > **Configuration** > **System Configuration** > **Log Daemon Configuration**, or run the `^LOGDMN` routine in the `%SYS` namespace. Three settings matter to Datadog:

   - Set **Format** to `JSON`. The default, `NVP`, is not parsed by this integration's log pipeline.
   - Set **Level** to the lowest severity you want to collect. The default, `WARN`, discards informational events.
   - Set the **child process launch command** to `irislogd -f <PATH>`, which chooses the file the Agent tails.

   From the `%SYS` namespace, the equivalent API calls are:

   ```objectscript
   do ##class(Config.Logging).Get(.props)
   set props("Format") = "JSON"
   set props("Level") = "INFO"
   set props("Enabled") = 1
   set props("ChildProcessLaunchCommand") = "irislogd -f /usr/irissys/mgr/structured.log"
   do ##class(Config.Logging).Modify(.props)
   do ##class(SYS.LogDmn).Start()
   ```

   Enabling the daemon does not start it. Start it from the Management Portal, or by calling `##class(SYS.LogDmn).Start()` as shown.

2. Add the structured log file to your log collection by editing the `logs` block in `intersystems_iris.d/conf.yaml`:

   ```yaml
   logs:
     - type: file
       path: /usr/irissys/mgr/structured.log
       source: intersystems_iris
       service: <SERVICE>
   ```

   Set `path` to the file you passed to `irislogd -f`.

3. Restart the Agent.

**Note**: At `INFO` and below, the structured log includes every audit event, and audit data can carry PII or PHI. The `%DirectMode` and `%SQL` event types are the most likely to do so. To keep that data out of Datadog, leave **Level** at `WARN` or higher, or restrict event types with the **Event Filter** setting.

**Note**: Messages that span several lines in `messages.log`, such as the journaling notices, appear in the structured log as their first line only. Collect `messages.log` instead if you need the continuation lines.

#### Collecting messages.log

1. Add the `messages.log` file to your log collection by editing the `logs` block in `intersystems_iris.d/conf.yaml`:

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

2. Restart the Agent.

**Note**: InterSystems IRIS writes timestamps in the instance's local time with no timezone offset, in both `messages.log` and the structured log. The log pipeline interprets them as UTC. If your IRIS instance does not run in UTC, collected log timestamps are shifted by the instance's UTC offset. Run your IRIS instance in UTC to keep log timestamps accurate.

## Data collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Tags

Two labels from the IRIS metrics endpoint are submitted under a different tag key, because their original names collide with the special meaning Datadog attaches to `host` and `version`. The values are preserved. Only the key changes:

| IRIS label | Datadog tag     | Metrics affected                | Description                                        |
| ---------- | --------------- | ------------------------------- | -------------------------------------------------- |
| `host`     | `interop_host`  | `intersystems_iris.interop.*`   | Business host name, not the reporting infrastructure host. |
| `version`  | `iris_version`  | `intersystems_iris.system.info` | IRIS product version, not the Agent version.       |

Scope your dashboards and monitors on the Datadog tag key. Every other endpoint label is submitted under its original name.

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
[10]: https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=GCM_structuredlog
