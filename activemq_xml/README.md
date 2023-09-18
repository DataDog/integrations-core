# ActiveMQ XML Integration

## Overview

Get metrics from ActiveMQ XML in real time to:

- Visualize and monitor ActiveMQ XML states.
- Be notified about ActiveMQ XML failovers and events.

## Setup

### Installation

The ActiveMQ XML check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your servers.

### Configuration

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

1. Edit `activemq_xml.d/conf.yaml`, in the `conf.d/` folder at the root of your [Agent's configuration directory][2] with your stats `url`. See the [sample activemq_xml.d/conf.yaml][3] for all available configuration options.

   **Note**: The ActiveMQ XML integration can potentially emit [custom metrics][4], which may impact your [billing][5]. By default, there is a limit of 350 metrics. If you require additional metrics, contact [Datadog support][6].

2. [Restart the Agent][7].

##### Log collection

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

2. Add this configuration block to your `activemq_xml.d/conf.yaml` or `activemq.d/conf.yaml` file to start collecting your ActiveMQ logs:

   ```yaml
   logs:
     - type: file
       path: "<ACTIVEMQ_BASEDIR>/data/activemq.log"
       source: activemq
       service: "<SERVICE_NAME>"
     - type: file
       path: "<ACTIVEMQ_BASEDIR>/data/audit.log"
       source: activemq
       service: "<SERVICE_NAME>"
   ```

3. [Restart the Agent][7].

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

For containerized environments, see the [Autodiscovery with JMX][8] guide.

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's status subcommand][9] and look for `activemq_xml` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][10] for a list of metrics provided by this integration.

### Events

The ActiveMQ XML check does not include any events.

### Service Checks

The ActiveMQ XML check does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][6].

## Further Reading

- [Monitor ActiveMQ metrics and performance][11]

[1]: https://app.datadoghq.com/account/settings/agent/latest
[2]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[3]: https://github.com/DataDog/integrations-core/blob/master/activemq_xml/datadog_checks/activemq_xml/data/conf.yaml.example
[4]: https://docs.datadoghq.com/developers/metrics/custom_metrics/
[5]: https://docs.datadoghq.com/account_management/billing/custom_metrics/
[6]: https://docs.datadoghq.com/help/
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[8]: https://docs.datadoghq.com/agent/guide/autodiscovery-with-jmx/?tab=containerizedagent
[9]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[10]: https://github.com/DataDog/integrations-core/blob/master/activemq_xml/metadata.csv
[11]: https://www.datadoghq.com/blog/monitor-activemq-metrics-performance
