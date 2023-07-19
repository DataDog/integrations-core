# Agent Check: TCP connectivity

![Network Graph][1]

## Overview

Monitor TCP connectivity and response time for any host and port.

## Setup

### Installation

The TCP check is included in the [Datadog Agent][2] package. No additional installation is needed on your server.

Many metrics checks are best run on the same host(s) as the monitored service. However, it's recommended to run this check from hosts that do not run the monitored TCP services to test remote connectivity.

### Configuration

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

Edit the `tcp_check.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][3]. See the [sample tcp_check.d/conf.yaml][4] for all available configuration options:

```yaml
init_config:

instances:
  - name: SSH check
    host: jumphost.example.com # or an IPv4/IPv6 address
    port: 22
    collect_response_time: true # to collect network.tcp.response_time. Default is false.
```

Configuration Options:

- `name` (Required) - Name of the service. This is included as a tag: `instance:<name>`. **Note**: Any spaces or dashes are converted to underscores.
- `host` (Required) - Host to be checked. This is included as a tag: `url:<host>:<port>`.
- `port` (Required) - Port to be checked. This is included as a tag: `url:<host>:<port>`.
- `timeout` (Optional) - Timeout for the check. Defaults to 10 seconds.
- `collect_response_time` (Optional) - Defaults to false, which means no response time metric is collected. If set to true, the metric returned is `network.tcp.response_time`.
- `tags` (Optional) - Tags to be assigned to the metric.

[Restart the Agent][5] to start sending TCP service checks and response times to Datadog.

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][6] for guidance on applying the parameters below.

| Parameter            | Value                                                                         |
| -------------------- | ----------------------------------------------------------------------------- |
| `<INTEGRATION_NAME>` | `tcp_check`                                                                   |
| `<INIT_CONFIG>`      | blank or `{}`                                                                 |
| `<INSTANCE_CONFIG>`  | `{"name": "<TCP_CHECK_INSTANCE_NAME>", "host":"%%host%%", "port":"%%port%%"}` |

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's `status` subcommand][7] and look for `tcp_check` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][8] for a list of metrics provided by this check.

### Events

The TCP check does not include any events.

### Service Checks

See [service_checks.json][9] for a list of service checks provided by this integration.

**Note:** To set an alert on this service check, create a [Network Monitor][10].

## Troubleshooting

Need help? Contact [Datadog support][11].

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/tcp_check/images/netgraphs.png
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/tcp_check/datadog_checks/tcp_check/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/tcp_check/metadata.csv
[9]: https://github.com/DataDog/integrations-core/blob/master/tcp_check/assets/service_checks.json
[10]: https://docs.datadoghq.com/monitors/monitor_types/network/?tab=checkalert
[11]: https://docs.datadoghq.com/help/
