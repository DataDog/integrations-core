# Activemq_xml Integration

## Overview

Get metrics from ActiveMQ XML service in real time to:

* Visualize and monitor ActiveMQ XML states
* Be notified about ActiveMQ XML failovers and events.

## Setup
### Installation

The Activemq XML check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your servers.

### Configuration

1. Edit the `activemq_xml.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][9], to point to your server and port, set the masters to monitor.

    See the [sample activemq_xml.d/conf.yaml][2] for all available configuration options.

2. [Restart the Agent][7]

### Validation

[Run the Agent's `status` subcommand][3] and look for `activemq_xml` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv][4] for a list of metrics provided by this integration.

### Events
The ActiveMQ XML check does not include any events at this time.

### Service Checks
The ActiveMQ XML check does not include any service checks at this time.

## Troubleshooting
Need help? Contact [Datadog Support][5].

## Further Reading

* [Monitor ActiveMQ metrics and performance][6]


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/activemq_xml/datadog_checks/activemq_xml/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[4]: https://github.com/DataDog/integrations-core/blob/master/activemq_xml/metadata.csv
[5]: https://docs.datadoghq.com/help/
[6]: https://www.datadoghq.com/blog/monitor-activemq-metrics-performance/
[7]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[8]: https://github.com/DataDog/integrations-core/blob/master/docs/index.md
[9]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
