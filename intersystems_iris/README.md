# Agent Check: InterSystems IRIS

## Overview

This check monitors [InterSystems IRIS][1] through the Datadog Agent. To learn more, see the [InterSystems IRIS integration documentation][2].

InterSystems IRIS is a data platform combining a multi-model database, an interoperability engine, and an analytics layer. This integration scrapes the built-in `/api/monitor/metrics` OpenMetrics endpoint, providing visibility into platform health without requiring additional instrumentation.

### What this integration monitors

- **Enterprise Cache Protocol (ECP)**: client and server block transfers, connection state, and latency across distributed deployments.
- **Interoperability**: production, business host, and queue activity for interoperability namespaces.
- **Write daemon and journaling**: write daemon cycle timing, WIJ activity, and journal entry throughput.
- **Mirroring**: mirror member status, journal transfer latency, and dejournaling backlog.
- **Caches and databases**: global, routine, and object cache efficiency, database growth, and directory space.
- **SQL**: statement counts, cached query inventory, and per-namespace query activity.
- **Processes and work queues**: process counts by state, work queue manager activity, and shared memory heap usage.
- **System and host**: CPU usage, paging, disk utilization, license consumption, and CSP gateway activity.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The InterSystems IRIS check is included in the [Datadog Agent][4] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `intersystems_iris.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory, to start collecting your InterSystems IRIS performance data. See the [sample intersystems_iris.d/conf.yaml][5] for all available configuration options.

2. At minimum, configure the `openmetrics_endpoint`:

   ```yaml
   instances:
     - openmetrics_endpoint: http://localhost:52773/api/monitor/metrics
   ```

   This endpoint is unauthenticated by default. If you have secured it, use the `auth_token`, `username` and `password`, or `headers` options.

3. Interoperability metrics (`intersystems_iris.interop.*`) are only emitted once the "Record Statistics for SAM" setting is enabled (`^Ens.Config("Stats","RecordSAM")=1`) in a namespace with a running production. Enable it if you want interoperability visibility.

4. [Restart the Agent][6].

### Log collection

_Available for Agent versions 6.0 and later._

InterSystems IRIS can channel all of its log information into a single machine-readable file called the [structured log][7]. This is the recommended log source: in JSON format each entry is a self-contained object on one line, so the Agent parses it into structured attributes without any custom processing rules. The structured log is a superset of `messages.log` and also carries audit events.

#### Option 1: Structured log (recommended)

1. Enable structured logging in IRIS. In the Management Portal, go to **System > Configuration > System Configuration > Log Daemon Configuration** and set:

   | Setting                      | Value                                                                  |
   | ---------------------------- | ---------------------------------------------------------------------- |
   | Enabled                      | `YES`                                                                  |
   | Child Process Launch Command | `irislogd -f /var/log/iris/structured.log -h <HOSTNAME> -i <INSTANCE>` |
   | Format                       | `JSON`                                                                 |
   | Level                        | `WARN` (default) or lower                                              |

   Replace the path with the destination file of your choice. The optional `-h` and `-i` arguments stamp each entry with the host and instance name. You can apply the same configuration with the `^LOGDMN` routine or the `SYS.LogDmn` class API in the `%SYS` namespace.

   **Note**: At log level `INFO` or lower, the structured log includes audit events, which can contain PII or PHI, particularly `%DirectMode` and `%SQL` event types. Keep the level at `WARN` or higher, or use the Event Filter (for example, `-Audit.*`) to exclude them.

   **Note**: If you already forward IRIS telemetry to an OpenTelemetry-compatible destination using OTLP/HTTP, that carries the same information and enabling structured logging is not necessary.

2. Collecting logs is disabled by default in the Datadog Agent. Enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

3. Add this configuration block to your `intersystems_iris.d/conf.yaml` file, pointing `path` at the file you configured in step 1:

   ```yaml
   logs:
     - type: file
       path: /var/log/iris/structured.log
       source: intersystems_iris
       service: <SERVICE_NAME>
   ```

   Each entry carries `when`, `pid`, `level`, `event`, and `text`, plus `host`, `instance`, `namespace`, `source`, `type`, and `group` where applicable.

4. [Restart the Agent][6].

#### Option 2: messages.log

If you cannot enable structured logging, collect `messages.log` directly. Entries span multiple lines, so a `multi_line` rule is required:

```yaml
logs:
  - type: file
    path: /usr/irissys/mgr/messages.log
    source: intersystems_iris
    service: <SERVICE_NAME>
    log_processing_rules:
      - type: multi_line
        name: new_log_start_with_date
        # pattern to match: 08/17/26-13:18:52:293
        pattern: \d{2}/\d{2}/\d{2}-\d{2}:\d{2}:\d{2}
```

For containerized environments, follow the instructions on the [Kubernetes Log Collection][8] or [Docker Log Collection][9] pages.

### Validation

[Run the Agent's status subcommand][10] and look for `intersystems_iris` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][11] for a list of metrics provided by this integration.

### Tags

Two labels from the IRIS metrics endpoint are submitted under a different tag key, because their original names collide with the special meaning Datadog attaches to `host` and `version`. The values are preserved. Only the key changes:

| IRIS label | Datadog tag     | Metrics affected                | Description                                                |
| ---------- | --------------- | ------------------------------- | ---------------------------------------------------------- |
| `host`     | `interop_host`  | `intersystems_iris.interop.*`   | Business host name, not the reporting infrastructure host.  |
| `version`  | `iris_version`  | `intersystems_iris.system.info` | IRIS product version, not the Agent version.               |

Scope your dashboards and monitors on the Datadog tag key. Every other endpoint label is submitted under its original name.

### Service Checks

**intersystems_iris.openmetrics.health**

Returns `CRITICAL` if the Agent is unable to connect to or parse the InterSystems IRIS OpenMetrics endpoint, otherwise returns `OK`.

## Troubleshooting

Need help? Contact [Datadog support][12].

[1]: https://www.intersystems.com/products/intersystems-iris/
[2]: https://docs.datadoghq.com/integrations/intersystems_iris/
[3]: https://docs.datadoghq.com/containers/kubernetes/integrations/
[4]: https://app.datadoghq.com/account/settings/agent/latest
[5]: https://github.com/DataDog/integrations-core/blob/master/intersystems_iris/datadog_checks/intersystems_iris/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/configuration/agent-commands/#start-stop-and-restart-the-agent
[7]: https://docs.intersystems.com/iris20262/csp/docbook/Doc.View.cls?KEY=GCM_structuredlog
[8]: https://docs.datadoghq.com/containers/kubernetes/log/
[9]: https://docs.datadoghq.com/containers/docker/log/
[10]: https://docs.datadoghq.com/agent/configuration/agent-commands/#agent-status-and-information
[11]: https://github.com/DataDog/integrations-core/blob/master/intersystems_iris/metadata.csv
[12]: https://docs.datadoghq.com/help/
