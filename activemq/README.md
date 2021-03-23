# ActiveMQ Integration

## Overview

The ActiveMQ check collects metrics for brokers and queues, producers and consumers, and more.

**Note:** This check also supports ActiveMQ Artemis (future ActiveMQ version `6`) and reports metrics under the `activemq.artemis` namespace. See [metrics metadata][9] for more details.

**Note**: If you are running a ActiveMQ version older than 5.8.0, see the [Agent 5.10.x released sample files][1].

## Setup

### Installation

The Agent's ActiveMQ check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your ActiveMQ nodes.

The check collects metrics via JMX, so you need a JVM on each node so the Agent can fork [jmxfetch][3]. We recommend using an Oracle-provided JVM.

### Configuration

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

1. **Make sure that [JMX Remote is enabled][4] on your ActiveMQ server.**
2. Configure the Agent to connect to ActiveMQ. Edit `activemq.d/conf.yaml`, in the `conf.d/` folder at the root of your [Agent's configuration directory][5]. See the [sample activemq.d/conf.yaml][6] for all available configuration options. See the [`metrics.yaml` file][15] for the list of default collected metrics.

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

3. [Restart the agent][7]

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

3. [Restart the Agent][7].

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][13] for guidance on applying the parameters below.

##### Metric collection

| Parameter            | Value                                |
| -------------------- | ------------------------------------ |
| `<INTEGRATION_NAME>` | `activemq`                           |
| `<INIT_CONFIG>`      | blank or `{}`                        |
| `<INSTANCE_CONFIG>`  | `{"host": "%%host%%","port":"1099"}` |

##### Log collection

_Available for Agent versions >6.0_

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes log collection documentation][14].

| Parameter      | Value                                                  |
| -------------- | ------------------------------------------------------ |
| `<LOG_CONFIG>` | `{"source": "activemq", "service": "<YOUR_APP_NAME>"}` |

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's status subcommand][8] and look for `activemq` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][9] for a list of metrics provided by this integration.  Metrics associated with ActiveMQ Artemis flavor have `artemis` in their metric name, all others are reported for ActiveMQ "classic".

### Events

The ActiveMQ check does not include any events.

### Service Checks

**activemq.can_connect**:<br>
Returns `CRITICAL` if the Agent is unable to connect to and collect metrics from the monitored ActiveMQ instance, otherwise returns `OK`.

## Troubleshooting

Need help? Contact [Datadog support][10].

## Further Reading

Additional helpful documentation, links, and articles:

- [ActiveMQ architecture and key metrics][11]
- [Monitor ActiveMQ metrics and performance][12]

[1]: https://raw.githubusercontent.com/DataDog/dd-agent/5.10.1/conf.d/activemq.yaml.example
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://github.com/DataDog/jmxfetch
[4]: https://activemq.apache.org/jmx.html
[5]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[6]: https://github.com/DataDog/integrations-core/blob/master/activemq/datadog_checks/activemq/data/conf.yaml.example
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[8]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[9]: https://github.com/DataDog/integrations-core/blob/master/activemq/metadata.csv
[10]: https://docs.datadoghq.com/help/
[11]: https://www.datadoghq.com/blog/activemq-architecture-and-metrics
[12]: https://www.datadoghq.com/blog/monitor-activemq-metrics-performance
[13]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[14]: https://docs.datadoghq.com/agent/kubernetes/log/?tab=containerinstallation#setup
[15]: https://github.com/DataDog/integrations-core/blob/master/activemq/datadog_checks/activemq/data/metrics.yaml
