# Agent Check: JBoss/WildFly

## Overview

This check monitors [JBoss][1] and [WildFly][2] applications.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The JBoss/WildFly check is included in the [Datadog Agent][4] package. No additional installation is needed on your server.

### Configuration

1. Edit the `jboss_wildfly.d/conf.yaml` file, in the `conf.d/` folder at the root of your
   Agent's configuration directory to start collecting your JBoss or WildFly application server's
   performance data. See the [sample jboss_wildfly.d/conf.yaml][5] for all available configuration options.

   This check has a limit of 350 metrics per instance. The number of returned metrics is indicated in the info page.
   You can specify the metrics you are interested in by editing the configuration below.
   To learn how to customize the collected metrics, visit the [JMX Checks documentation][6] for more detailed instructions.
   If you need to monitor more metrics, contact [Datadog support][7].

2. [Restart the Agent][8].

#### Log collection

**Available for Agent >6.0**

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

    ```yaml
      logs_enabled: true
    ```

2. Next, edit `jboss_wildfly.d/conf.yaml` by uncommenting the `logs` lines at the bottom. Update the logs `path` with the correct path to your JBoss log files.

    ```
      logs:
        - type: file
          path: /opt/jboss/wildfly/standalone/log/*.log
          source: jboss_wildfly
          service: <APPLICATION_NAME>
    ```

3. [Restart the Agent][8].

### Validation

[Run the Agent's status subcommand][9] and look for `jboss_wildfly` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][9] for a list of metrics provided by this integration.

### Events

The JBoss/WildFly integration does not include any events.

### Service Checks

The JBoss/WildFly integration does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][8].

[1]: https://developers.redhat.com/products/eap/overview
[2]: http://wildfly.org
[3]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[4]: https://app.datadoghq.com/account/settings#agent
[5]: https://github.com/DataDog/integrations-core/blob/master/jboss_wildfly/datadog_checks/jboss_wildfly/data/conf.yaml.example
[6]: https://docs.datadoghq.com/integrations/java
[7]: https://docs.datadoghq.com/help
[8]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-restart-the-agent
[9]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
