# ActiveMQ XML Integration

## Overview

Get metrics from ActiveMQ XML service in real time to:

* Visualize and monitor ActiveMQ XML states
* Be notified about ActiveMQ XML failovers and events.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][121] for guidance on applying these instructions.

### Installation

The ActiveMQ XML check is included in the [Datadog Agent][111] package, so you don't need to install anything else on your servers.

### Configuration

1. Edit `activemq_xml.d/conf.yaml`, in the `conf.d/` folder at the root of your [Agent's configuration directory][112] with your stats `url`. See the [sample activemq_xml.d/conf.yaml][113] for all available configuration options.

2. [Restart the Agent][114].

#### Metrics collection
The ActiveMQ XML integration can potentially emit [custom metrics][115], which may impact your [billing][116]. By default, there is a limit of 350 metrics. If you require additional metrics, contact [Datadog support][117].

### Validation

[Run the Agent's status subcommand][118] and look for `activemq_xml` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv][119] for a list of metrics provided by this integration.

### Events
The ActiveMQ XML check does not include any events.

### Service Checks
The ActiveMQ XML check does not include any service checks.

## Troubleshooting
Need help? Contact [Datadog support][117].

## Further Reading

* [Monitor ActiveMQ metrics and performance][120]


[111]: https://app.datadoghq.com/account/settings#agent
[112]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[113]: https://github.com/DataDog/integrations-core/blob/master/activemq_xml/datadog_checks/activemq_xml/data/conf.yaml.example
[114]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[115]: https://docs.datadoghq.com/developers/metrics/custom_metrics
[116]: https://docs.datadoghq.com/account_management/billing/custom_metrics
[117]: https://docs.datadoghq.com/help
[118]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[119]: https://github.com/DataDog/integrations-core/blob/master/activemq_xml/metadata.csv
[120]: https://www.datadoghq.com/blog/monitor-activemq-metrics-performance
[121]: https://docs.datadoghq.com/agent/autodiscovery/integrations
