# Mapreduce Integration

![MapReduce Dashboard][1]

## Overview

Get metrics from mapreduce service in real time to:

* Visualize and monitor mapreduce states
* Be notified about mapreduce failovers and events.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying these instructions.

### Installation

The Mapreduce check is included in the [Datadog Agent][3] package, so you don't need to install anything else on your servers.

### Configuration

Edit the `mapreduce.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][4] to point to your server and port, set the masters to monitor. See the [sample mapreduce.d/conf.yaml][5] for all available configuration options.

### Validation

[Run the Agent's `status` subcommand][6] and look for `mapreduce` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv][7] for a list of metrics provided by this integration.

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
Need help? Contact [Datadog support][8].

## Further Reading

* [Hadoop architectural overview][9]
* [How to monitor Hadoop metrics][10]
* [How to collect Hadoop metrics][11]
* [How to monitor Hadoop with Datadog][12]


[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/mapreduce/images/mapreduce_dashboard.png
[2]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[3]: https://app.datadoghq.com/account/settings#agent
[4]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[5]: https://github.com/DataDog/integrations-core/blob/master/mapreduce/datadog_checks/mapreduce/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/mapreduce/metadata.csv
[8]: https://docs.datadoghq.com/help
[9]: https://www.datadoghq.com/blog/hadoop-architecture-overview
[10]: https://www.datadoghq.com/blog/monitor-hadoop-metrics
[11]: https://www.datadoghq.com/blog/collecting-hadoop-metrics
[12]: https://www.datadoghq.com/blog/monitor-hadoop-metrics-datadog
