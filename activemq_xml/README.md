# ActiveMQ XML Integration

## Overview

Get metrics from ActiveMQ XML in real time to:

- Visualize and monitor ActiveMQ XML states.
- Be notified about ActiveMQ XML failovers and events.

## Setup

### Installation

The ActiveMQ XML check is included in the [Datadog Agent][111] package, so you don't need to install anything else on your servers.

### Configuration

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

#### Host

1. Edit `activemq_xml.d/conf.yaml`, in the `conf.d/` folder at the root of your [Agent's configuration directory][112] with your stats `url`. See the [sample activemq_xml.d/conf.yaml][113] for all available configuration options.

   **Note**: The ActiveMQ XML integration can potentially emit [custom metrics][114], which may impact your [billing][115]. By default, there is a limit of 350 metrics. If you require additional metrics, contact [Datadog support][116].

2. [Restart the Agent][117].

#### Containerized

For containerized environments, see the [Autodiscovery with JMX][118] guide.

### Validation

[Run the Agent's status subcommand][119] and look for `activemq_xml` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][1110] for a list of metrics provided by this integration.

### Events

The ActiveMQ XML check does not include any events.

### Service Checks

The ActiveMQ XML check does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][116].

## Further Reading

- [Monitor ActiveMQ metrics and performance][1111]

[111]: https://app.datadoghq.com/account/settings#agent
[112]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[113]: https://github.com/DataDog/integrations-core/blob/master/activemq_xml/datadog_checks/activemq_xml/data/conf.yaml.example
[114]: https://docs.datadoghq.com/developers/metrics/custom_metrics/
[115]: https://docs.datadoghq.com/account_management/billing/custom_metrics/
[116]: https://docs.datadoghq.com/help/
[117]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[118]: https://docs.datadoghq.com/agent/guide/autodiscovery-with-jmx/?tab=containerizedagent
[119]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[1110]: https://github.com/DataDog/integrations-core/blob/master/activemq_xml/metadata.csv
[1111]: https://www.datadoghq.com/blog/monitor-activemq-metrics-performance
