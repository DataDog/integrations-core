# Agent Check: TCP connectivity
{{< img src="integrations/tcpcheck/netgraphs.png" alt="Network Graphs" responsive="true" popup="true">}}
## Overview

Monitor TCP connectivity and response time for any host and port.

## Setup
### Installation

The TCP check is packaged with the Agent, so simply [install the Agent][1] on any host from which you want to probe TCP ports. Though many metrics-oriented checks are best run on the same host(s) as the monitored service, you'll probably want to run this check from hosts that do not run the monitored TCP services, i.e. to test remote connectivity.

### Configuration

Create a file `tcp_check.yaml` in the Agent's `conf.d` directory. See the [sample tcp_check.yaml][2] for all available configuration options:

```
init_config:

instances:
  - name: SSH check
    host: jumphost.example.com # or an IPv4/IPv6 address
    port: 22
    collect_response_time: true # to collect network.tcp.response_time. Default is false.
```

Configuration Options

* `name` (Required) - Name of the service. This will be included as a tag: `instance:<name>`. Note: This tag will have any spaces and dashes converted to underscores.
* `host` (Required) - Host to be checked. This will be included as a tag: `url:<host>:<port>`.
* `port` (Required) - Port to be checked. This will be included as a tag: `url:<host>:<port>`.
* `timeout` (Optional) - Timeout for the check. Defaults to 10 seconds.
* `collect_response_time` (Optional) - Defaults to false. If this is not set to true, no response time metric will be collected. If it is set to true, the metric returned is `network.tcp.response_time`.
* `tags` (Optional) - Tags to be assigned to the metric.

[Restart the Agent][3] to start sending TCP service checks and response times to Datadog.

### Validation

[Run the Agent's `status` subcommand][4] and look for `tcp_check` under the Checks section:

```
  Checks
  ======
    [...]

    tcp_check
    ----------
      - instance #0 [OK]
      - Collected 1 metric, 0 events & 1 service check

    [...]
```

## Compatibility

The TCP check is compatible with all major platforms.

## Data Collected
### Metrics

See [metadata.csv][5] for a list of metrics provided by this check.

### Events
The TCP check does not include any event at this time.

### Service Checks

**`tcp.can_connect`**:

Returns DOWN if the Agent cannot connect to the configured `host` and `port`, otherwise UP.

To create alert conditions on this service check in the Datadog app, click **Network** on the [Create Monitor][6] page, not **Integration**.

## Troubleshooting
Need help? Contact [Datadog Support][7].

## Further Reading
Learn more about infrastructure monitoring and all our integrations on [our blog][8]


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/tcp_check/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/tcp_check/metadata.csv
[6]: https://app.datadoghq.com/monitors#/create
[7]: http://docs.datadoghq.com/help/
[8]: https://www.datadoghq.com/blog/
