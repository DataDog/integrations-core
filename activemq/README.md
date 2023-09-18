# ActiveMQ Integration

## Overview

The ActiveMQ check collects metrics for brokers, queues, producers, consumers, and more.

**Note:** This check also supports ActiveMQ Artemis (future ActiveMQ version `6`) and reports metrics under the `activemq.artemis` namespace. See [metadata.csv][1] for a list of metrics provided by this integration.

**Note**: If you are running a ActiveMQ version older than 5.8.0, see the [Agent 5.10.x released sample files][2].

## Setup

### Installation

The Agent's ActiveMQ check is included in the [Datadog Agent][3] package, so you don't need to install anything else on your ActiveMQ nodes.

The check collects metrics from JMX with [JMXFetch][4]. A JVM is needed on each node so the Agent can run JMXFetch. Datadog recommends using an Oracle-provided JVM.

### Configuration

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

1. **Make sure that [JMX Remote is enabled][5] on your ActiveMQ server.**
2. Configure the Agent to connect to ActiveMQ. Edit `activemq.d/conf.yaml`, in the `conf.d/` folder at the root of your [Agent's configuration directory][6]. See the [sample activemq.d/conf.yaml][7] for all available configuration options. See the [`metrics.yaml` file][8] for the list of default collected metrics.

   ```yaml
   init_config:
     is_jmx: true
     collect_default_metrics: true

   instances:
     - host: localhost
       port: 1616
       user: username
       password: password
       name: activemq_instance
   ```

3. [Restart the agent][9]

##### Log collection

_Available for Agent versions >6.0_

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

2. Add this configuration block to your `activemq.d/conf.yaml` file to start collecting your ActiveMQ logs:

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

3. [Restart the Agent][9].

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][10] for guidance on applying the parameters below.

##### Metric collection

| Parameter            | Value                                |
| -------------------- | ------------------------------------ |
| `<INTEGRATION_NAME>` | `activemq`                           |
| `<INIT_CONFIG>`      | `"is_jmx": true`                     |
| `<INSTANCE_CONFIG>`  | `{"host": "%%host%%","port":"1099"}` |

##### Log collection

_Available for Agent versions >6.0_

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes Log Collection][11].

| Parameter      | Value                                                  |
| -------------- | ------------------------------------------------------ |
| `<LOG_CONFIG>` | `{"source": "activemq", "service": "<YOUR_APP_NAME>"}` |

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's status subcommand][12] and look for `activemq` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][1] for a list of metrics provided by this integration. Metrics associated with ActiveMQ Artemis flavor have `artemis` in their metric name, all others are reported for ActiveMQ "classic".

### Events

The ActiveMQ check does not include any events.

### Service Checks

See [service_checks.json][13] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][14].

## Further Reading

Additional helpful documentation, links, and articles:

- [ActiveMQ architecture and key metrics][15]
- [Monitor ActiveMQ metrics and performance][16]

[1]: https://github.com/DataDog/integrations-core/blob/master/activemq/metadata.csv
[2]: https://raw.githubusercontent.com/DataDog/dd-agent/5.10.1/conf.d/activemq.yaml.example
[3]: https://app.datadoghq.com/account/settings/agent/latest
[4]: https://github.com/DataDog/jmxfetch
[5]: https://activemq.apache.org/jmx.html
[6]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[7]: https://github.com/DataDog/integrations-core/blob/master/activemq/datadog_checks/activemq/data/conf.yaml.example
[8]: https://github.com/DataDog/integrations-core/blob/master/activemq/datadog_checks/activemq/data/metrics.yaml
[9]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[10]: https://docs.datadoghq.com/containers/guide/autodiscovery-with-jmx/?tab=containeragent
[11]: https://docs.datadoghq.com/agent/kubernetes/log/
[12]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[13]: https://github.com/DataDog/integrations-core/blob/master/activemq/assets/service_checks.json
[14]: https://docs.datadoghq.com/help/
[15]: https://www.datadoghq.com/blog/activemq-architecture-and-metrics
[16]: https://www.datadoghq.com/blog/monitor-activemq-metrics-performance
