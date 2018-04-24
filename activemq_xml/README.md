# Activemq_xml Integration

## Overview

Get metrics from activemq_xml service in real time to:

* Visualize and monitor activemq_xml states
* Be notified about activemq_xml failovers and events.

## Setup
### Installation

The Activemq XML check is packaged with the Agent, so simply [install the Agent][1] on your servers.

### Configuration

Edit the `activemq_xml.yaml` file to point to your server and port, set the masters to monitor. See the [sample activemq_xml.yaml][2] for all available configuration options.

### Validation

[Run the Agent's `status` subcommand][3] and look for `activemq_xml` under the Checks section:

    Checks
    ======

        activemq_xml
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The activemq_xml check is compatible with all major platforms

## Data Collected
### Metrics
See [metadata.csv][4] for a list of metrics provided by this integration.

### Events
The Activemq_xml check does not include any event at this time.

### Service Checks
The Activemq_xml check does not include any service check at this time.

## Troubleshooting
Need help? Contact [Datadog Support][5].

## Further Reading

* [Monitor ActiveMQ metrics and performance][6]


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/activemq_xml/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[4]: https://github.com/DataDog/integrations-core/blob/master/activemq_xml/metadata.csv
[5]: http://docs.datadoghq.com/help/
[6]: https://www.datadoghq.com/blog/monitor-activemq-metrics-performance/
