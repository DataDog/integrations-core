# Activemq_xml Integration

## Overview

Get metrics from ActiveMQ XML service in real time to:

* Visualize and monitor ActiveMQ XML states
* Be notified about ActiveMQ XML failovers and events.

## Setup
### Installation

The ActiveMQ XML check is included in the [Datadog Agent][11] package, so you don't need to install anything else on your servers.

### Configuration

1. Edit `activemq_xml.d/conf.yaml`, in the `conf.d/` folder at the root of your [Agent's configuration directory][12] with your stats `url`.

    See the [sample activemq_xml.d/conf.yaml][13] for all available configuration options.

2. [Restart the Agent][14]

### Validation

[Run the Agent's `status` subcommand][15] and look for `activemq_xml` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv][16] for a list of metrics provided by this integration.

### Events
The ActiveMQ XML check does not include any events.

### Service Checks
The ActiveMQ XML check does not include any service checks.

## Troubleshooting
Need help? Contact [Datadog support][17].

## Further Reading

* [Monitor ActiveMQ metrics and performance][18]


[11]: https://app.datadoghq.com/account/settings#agent
[12]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/?tab=agentv6#agent-configuration-directory
[13]: https://github.com/DataDog/integrations-core/blob/master/activemq_xml/datadog_checks/activemq_xml/data/conf.yaml.example
[14]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[15]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[16]: https://github.com/DataDog/integrations-core/blob/master/activemq_xml/metadata.csv
[17]: https://docs.datadoghq.com/help
[18]: https://www.datadoghq.com/blog/monitor-activemq-metrics-performance
