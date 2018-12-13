# Mapreduce Integration

![MapReduce Dashboard][1]

## Overview

Get metrics from mapreduce service in real time to:

* Visualize and monitor mapreduce states
* Be notified about mapreduce failovers and events.

## Setup
### Installation

The Mapreduce check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your servers.

### Configuration

Edit the `mapreduce.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][3] to point to your server and port, set the masters to monitor. See the [sample mapreduce.d/conf.yaml][4] for all available configuration options.

### Validation

[Run the Agent's `status` subcommand][5] and look for `mapreduce` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv][6] for a list of metrics provided by this integration.

### Events
The Mapreduce check does not include any events at this time.

### Service Checks
**mapreduce.resource_manager.can_connect**

Returns `CRITICAL` if the Agent is unable to connect to the Resource Manager.
Returns `OK` otherwise.

**mapreduce.application_master.can_connect**

Returns `CRITICAL` if the Agent is unable to connect to the Application Master.
Returns `OK` otherwise.

## Troubleshooting
Need help? Contact [Datadog Support][7].

## Further Reading

* [Hadoop architectural overview][8]
* [How to monitor Hadoop metrics][9]
* [How to collect Hadoop metrics][10]
* [How to monitor Hadoop with Datadog][11]


[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/mapreduce/images/mapreduce_dashboard.png
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/mapreduce/datadog_checks/mapreduce/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/mapreduce/metadata.csv
[7]: https://docs.datadoghq.com/help
[8]: https://www.datadoghq.com/blog/hadoop-architecture-overview
[9]: https://www.datadoghq.com/blog/monitor-hadoop-metrics
[10]: https://www.datadoghq.com/blog/collecting-hadoop-metrics
[11]: https://www.datadoghq.com/blog/monitor-hadoop-metrics-datadog
