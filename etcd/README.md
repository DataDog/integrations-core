# Etcd Integration

![Etcd Dashboard][1]

## Overview

Collect Etcd metrics to:

- Monitor the health of your Etcd cluster.
- Know when host configurations may be out of sync.
- Correlate the performance of Etcd with the rest of your applications.

## Setup

### Installation

The Etcd check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your Etcd instance(s).

### Configuration

#### Host

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

1. Edit the `etcd.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][3] to start collecting your Etcd performance data. See the [sample etcd.d/conf.yaml][4] for all available configuration options.
2. [Restart the Agent][5]

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][6] for guidance on applying the parameters below.

| Parameter            | Value                                                |
| -------------------- | ---------------------------------------------------- |
| `<INTEGRATION_NAME>` | `etcd`                                               |
| `<INIT_CONFIG>`      | blank or `{}`                                        |
| `<INSTANCE_CONFIG>`  | `{"prometheus_url": "http://%%host%%:2379/metrics"}` |

### Validation

[Run the Agent's `status` subcommand][7] and look for `etcd` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][8] for a list of metrics provided by this integration.

Etcd metrics are tagged with `etcd_state:leader` or `etcd_state:follower`, depending on the node status, so you can easily aggregate metrics by status.

### Events

The Etcd check does not include any events.

### Service Checks

`etcd.can_connect`:

Returns 'Critical' if the Agent cannot collect metrics from your Etcd API endpoint.

`etcd.healthy`:

Returns 'Critical' if a member node is not healthy. Returns 'Unknown' if the Agent can't reach the `/health` endpoint, or if the health status is missing.

## Troubleshooting

Need help? Contact [Datadog support][9].

## Further Reading

To get a better idea of how (or why) to integrate Etcd with Datadog, check out our [blog post][10] about it.

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/etcd/images/etcd_dashboard.png
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/etcd/datadog_checks/etcd/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/etcd/metadata.csv
[9]: https://docs.datadoghq.com/help
[10]: https://www.datadoghq.com/blog/monitor-etcd-performance
