# Agent Check: TCP connectivity

![Network Graph][1]

## Overview

Monitor TCP connectivity and response time for any host and port.

## Setup

### Installation

The TCP check is included in the [Datadog Agent][3] package, so you don't need to install anything else on any host from which you will probe TCP ports. Though many metrics-oriented checks are best run on the same host(s) as the monitored service, you'll probably want to run this check from hosts that do not run the monitored TCP services, i.e. to test remote connectivity.

### Configuration

#### Host

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

Edit the `tcp_check.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][4]. See the [sample tcp_check.d/conf.yaml][5] for all available configuration options:

```yaml
init_config:

instances:
  - name: SSH check
    host: jumphost.example.com # or an IPv4/IPv6 address
    port: 22
    collect_response_time: true # to collect network.tcp.response_time. Default is false.
```

Configuration Options:

- `name` (Required) - Name of the service. This will be included as a tag: `instance:<name>`. Note: This tag will have any spaces and dashes converted to underscores.
- `host` (Required) - Host to be checked. This will be included as a tag: `url:<host>:<port>`.
- `port` (Required) - Port to be checked. This will be included as a tag: `url:<host>:<port>`.
- `timeout` (Optional) - Timeout for the check. Defaults to 10 seconds.
- `collect_response_time` (Optional) - Defaults to false. If this is not set to true, no response time metric will be collected. If it is set to true, the metric returned is `network.tcp.response_time`.
- `tags` (Optional) - Tags to be assigned to the metric.

[Restart the Agent][6] to start sending TCP service checks and response times to Datadog.

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying the parameters below.

| Parameter            | Value                                                                         |
| -------------------- | ----------------------------------------------------------------------------- |
| `<INTEGRATION_NAME>` | `tcp_check`                                                                   |
| `<INIT_CONFIG>`      | blank or `{}`                                                                 |
| `<INSTANCE_CONFIG>`  | `{"name": "<TCP_CHECK_INSTANCE_NAME>", "host":"%%host%%", "port":"%%port%%"}` |

### Validation

[Run the Agent's `status` subcommand][7] and look for `tcp_check` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][8] for a list of metrics provided by this check.

### Events

The TCP check does not include any events.

### Service Checks

**`tcp.can_connect`**:

Returns DOWN if the Agent cannot connect to the configured `host` and `port`, otherwise UP.

To create alert conditions on this service check in Datadog, click **Network** on the [Create Monitor][9] page, not **Integration**.

## Troubleshooting

Need help? Contact [Datadog support][10].

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/tcp_check/images/netgraphs.png
[2]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[3]: https://app.datadoghq.com/account/settings#agent
[4]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[5]: https://github.com/DataDog/integrations-core/blob/master/tcp_check/datadog_checks/tcp_check/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/tcp_check/metadata.csv
[9]: https://app.datadoghq.com/monitors#/create
[10]: https://docs.datadoghq.com/help/
