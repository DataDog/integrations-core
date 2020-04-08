# Agent Check: JBoss/WildFly

## Overview

This check monitors [JBoss][1] and [WildFly][2] applications.

## Setup

### Installation

The JBoss/WildFly check is included in the [Datadog Agent][3] package. 

Depending on your server setup (particularly when using the `remote+http` JMX scheme), you may need to specify a custom JAR to connect to the server. 

Place the JAR on the same machine as your Agent, and add the path to the `custom_jar_paths` option.

   **Note**: The JMX url scheme is different according to your WildFly version.

   For Wildfly 9 and older:

   `service:jmx:http-remoting-jmx://<host>:<port> `
   
   For Wildfly 10+:

   `service:jmx:remote+http://<host>:<port>`

Please refer to the [WildFly JMX subsystem configuration page](https://docs.jboss.org/author/display/WFLY9/JMX%20subsystem%20configuration.html) for more information

### Configuration

#### Host

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

##### Metric collection

1. Edit the `jboss_wildfly.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your JBoss or WildFly application server's performance data. See the [sample jboss_wildfly.d/conf.yaml][4] for all available configuration options.

    **Note**:This check has a limit of 350 metrics per instance. The number of returned metrics is indicated in the info page. You can specify the metrics you are interested in by editing the configuration below. To learn how to customize the collected metrics, visit the [JMX Checks documentation][5] for more detailed instructions. If you need to monitor more metrics, contact [Datadog support][6].

2. [Restart the Agent][7].

##### Log collection

_Available for Agent versions >6.0_

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

2. Next, edit `jboss_wildfly.d/conf.yaml` by uncommenting the `logs` lines at the bottom. Update the logs `path` with the correct path to your JBoss log files.

   ```yaml
   logs:
     - type: file
       path: /opt/jboss/wildfly/standalone/log/*.log
       source: jboss_wildfly
       service: '<APPLICATION_NAME>'
   ```

3. [Restart the Agent][7].

#### Containerized

##### Metric collection

For containerized environments, see the [Autodiscovery with JMX][8] guide.

##### Log collection

_Available for Agent versions >6.0_

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Docker log collection][9].

| Parameter      | Value                                                      |
| -------------- | ---------------------------------------------------------- |
| `<LOG_CONFIG>` | `{"source": "jboss_wildfly", "service": "<SERVICE_NAME>"}` |

### Validation

[Run the Agent's status subcommand][10] and look for `jboss_wildfly` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][11] for a list of metrics provided by this integration.

### Events

The JBoss/WildFly integration does not include any events.

### Service Checks

**jboss.can_connect**:<br>
Returns `CRITICAL` if the Agent is unable to connect to and collect metrics from the monitored JBoss/WildFly instance, otherwise returns `OK`.

## Troubleshooting

Need help? Contact [Datadog support][6].

[1]: https://developers.redhat.com/products/eap/overview
[2]: http://wildfly.org
[3]: https://app.datadoghq.com/account/settings#agent
[4]: https://github.com/DataDog/integrations-core/blob/master/jboss_wildfly/datadog_checks/jboss_wildfly/data/conf.yaml.example
[5]: https://docs.datadoghq.com/integrations/java
[6]: https://docs.datadoghq.com/help
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-restart-the-agent
[8]: https://docs.datadoghq.com/agent/guide/autodiscovery-with-jmx/?tab=containerizedagent
[9]: https://docs.datadoghq.com/agent/docker/log/
[10]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[11]: https://github.com/DataDog/integrations-core/blob/master/jboss_wildfly/metadata.csv
