# Agent Check: NiFi

## Overview

This check monitors [Apache NiFi][1] through the Datadog Agent.

Apache NiFi is an open-source platform for routing, transforming, and automating data flow between systems. This check collects JVM health, flow throughput, queue backpressure, processor status, and bulletin events from the NiFi REST API. No NiFi-side reporting task or JMX exporter is required.

With the Datadog NiFi integration, you can:

- Monitor JVM memory, garbage collection, and thread activity.
- Track flow throughput, queued flowfiles, and backpressure across process groups.
- Surface processor status at configurable cardinality, with opt-in per-processor and per-connection metrics.
- Receive NiFi bulletins (errors and warnings) as Datadog events.
- Collect application, user, bootstrap, and request logs.

**Minimum Agent version:** <!-- TODO(AI-6674): set to the first Agent release that ships the NiFi check before public release. -->

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The NiFi check is included in the [Datadog Agent][2] package. No additional installation is needed on your server.

### Configuration

#### Host

1. Edit the `nifi.d/conf.yaml` file in the `conf.d/` folder at the root of your Agent's configuration directory. See the [sample nifi.d/conf.yaml][4] for all available configuration options.

2. At minimum, configure `api_url`, `username`, and `password`:

   ```yaml
   instances:
     - api_url: https://localhost:8443/nifi-api
       username: <NIFI_USERNAME>
       password: <NIFI_PASSWORD>
       tls_verify: true
   ```

3. [Restart the Agent][5].

#### Containerized (Autodiscovery)

For containerized NiFi, apply the following annotations to the NiFi pod. Adjust the container name in the annotation key to match your deployment.

```yaml
ad.datadoghq.com/nifi.checks: |
  {
    "nifi": {
      "instances": [
        {
          "api_url": "https://%%host%%:8443/nifi-api",
          "username": "<NIFI_USERNAME>",
          "password": "<NIFI_PASSWORD>",
          "tls_verify": true
        }
      ]
    }
  }
```

Store credentials in Kubernetes secrets and reference them through standard secret-injection patterns rather than inline in annotations. For more information, see the [Autodiscovery Integration Templates][3].

### Validation

[Run the Agent's status subcommand][6] and look for `nifi` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this check.

Per-connection and per-processor metrics are opt-in to control cardinality. Enable them with `collect_connection_metrics: true` and `collect_processor_metrics: true`. Use `max_connections` and `max_processors` to cap the number of entities monitored.

### Events

NiFi bulletins (errors and warnings from processors and system components) are forwarded as Datadog events when `collect_bulletins` is enabled (default: `true`). Filter by severity with `bulletin_min_level` (default: `WARNING`).

### Service Checks

The NiFi check does not include any service checks. Connectivity is reported with the `nifi.can_connect` gauge (`1` = OK, `0` = unreachable).

## Troubleshooting

### Authentication fails (`nifi.can_connect` = 0)

The check authenticates to NiFi with `POST /access/token` (JWT bearer token). If authentication fails, the Agent log records an error from the `nifi` check. Common causes:

- Wrong `username` or `password`.
- The NiFi user lacks sufficient permissions. The check reads `/flow/about`, `/flow/status`, `/flow/cluster/summary`, `/system-diagnostics`, `/flow/bulletin-board`, and `/flow/process-groups/{id}/status`. Grant the user read access on those resources. See the [NiFi System Administrator's Guide][10] for configuring access policies.
- The configured NiFi identity provider (LDAP, Kerberos, certificates) rejects the credentials. Confirm the credentials work against the NiFi UI first.

### TLS verification errors

NiFi 2.x uses HTTPS by default, and most production deployments use an internal or self-signed CA. Point the check at your CA bundle:

```yaml
tls_ca_cert: /path/to/ca.pem
```

As a last resort (not recommended for production), set `tls_verify: false`.

### Missing per-connection or per-processor metrics

Per-connection and per-processor metrics are opt-in. Set `collect_connection_metrics: true` and `collect_processor_metrics: true`. The check truncates output to `max_connections` and `max_processors` (default `200` each), prioritizing the busiest entities by queue depth and task count.

### Still stuck?

Contact [Datadog support][8].

## Further Reading

- [Apache NiFi REST API documentation][9]
- [Apache NiFi System Administrator's Guide][10]


[1]: https://nifi.apache.org/
[2]: /account/settings/agent/latest
[3]: https://docs.datadoghq.com/containers/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/nifi/datadog_checks/nifi/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/configuration/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/configuration/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/nifi/metadata.csv
[8]: https://docs.datadoghq.com/help/
[9]: https://nifi.apache.org/docs/nifi-docs/rest-api/
[10]: https://nifi.apache.org/docs/nifi-docs/html/administration-guide.html
