# Activemq_xml Integration

## Overview

Get metrics from ActiveMQ XML service in real time to:

* Visualize and monitor ActiveMQ XML states
* Be notified about ActiveMQ XML failovers and events.

## Setup
### Installation

The ActiveMQ XML check is included in the [Datadog Agent][111] package, so you don't need to install anything else on your servers.

### Configuration

1. Edit `activemq_xml.d/conf.yaml`, in the `conf.d/` folder at the root of your [Agent's configuration directory][112] with your stats `url`.

    See the [sample activemq_xml.d/conf.yaml][113] for all available configuration options.

2. [Restart the Agent][114]

### Validation

[Run the Agent's `status` subcommand][115] and look for `activemq_xml` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv][116] for a list of metrics provided by this integration.

### Events
The ActiveMQ XML check does not include any events.

### Service Checks
The ActiveMQ XML check does not include any service checks.

## Troubleshooting
Need help? Contact [Datadog support][117].

## Further Reading

* [Monitor ActiveMQ metrics and performance][118]


[111]: https://app.datadoghq.com/account/settings#agent
[112]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/?tab=agentv6#agent-configuration-directory
[113]: https://github.com/DataDog/integrations-core/blob/master/activemq_xml/datadog_checks/activemq_xml/data/conf.yaml.example
[114]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[115]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[116]: https://github.com/DataDog/integrations-core/blob/master/activemq_xml/metadata.csv
[117]: https://docs.datadoghq.com/help
[118]: https://www.datadoghq.com/blog/monitor-activemq-metrics-performance
