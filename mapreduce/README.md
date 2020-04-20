# Mapreduce Integration

![MapReduce Dashboard][1]

## Overview

Get metrics from mapreduce service in real time to:

- Visualize and monitor mapreduce states
- Be notified about mapreduce failovers and events.

## Setup

### Installation

The Mapreduce check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your servers.

### Configuration

#### Host

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

1. Edit the `mapreduce.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][3] to point to your server and port, set the masters to monitor. See the [sample mapreduce.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][6] for guidance on applying the parameters below.

| Parameter            | Value                                                                                         |
| -------------------- | --------------------------------------------------------------------------------------------- |
| `<INTEGRATION_NAME>` | `mapreduce`                                                                                   |
| `<INIT_CONFIG>`      | blank or `{}`                                                                                 |
| `<INSTANCE_CONFIG>`  | `{"resourcemanager_uri": "https://%%host%%:8088", "cluster_name":"<MAPREDUCE_CLUSTER_NAME>"}` |

### Validation

[Run the Agent's status subcommand][7] and look for `mapreduce` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][8] for a list of metrics provided by this integration.

### Events

The Mapreduce check does not include any events.

### Service Checks

**mapreduce.resource_manager.can_connect**

Returns `CRITICAL` if the Agent is unable to connect to the Resource Manager.
Returns `OK` otherwise.

**mapreduce.application_master.can_connect**

Returns `CRITICAL` if the Agent is unable to connect to the Application Master.
Returns `OK` otherwise.

## Troubleshooting

Need help? Contact [Datadog support][9].

## Further Reading

- [Hadoop architectural overview][10]
- [How to monitor Hadoop metrics][11]
- [How to collect Hadoop metrics][12]
- [How to monitor Hadoop with Datadog][13]

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/mapreduce/images/mapreduce_dashboard.png
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/mapreduce/datadog_checks/mapreduce/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#restart-the-agent
[6]: https://docs.datadoghq.com/agent/kubernetes/integrations
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/mapreduce/metadata.csv
[9]: https://docs.datadoghq.com/help
[10]: https://www.datadoghq.com/blog/hadoop-architecture-overview
[11]: https://www.datadoghq.com/blog/monitor-hadoop-metrics
[12]: https://www.datadoghq.com/blog/collecting-hadoop-metrics
[13]: https://www.datadoghq.com/blog/monitor-hadoop-metrics-datadog
