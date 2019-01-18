# Agent Check: JBoss/Wildfly

## Overview

This check monitors [JBoss][1] and [Wildfly][2] applications.

## Setup

### Installation

The JBoss/Wildfly check is included in the [Datadog Agent][3] package, so you do not
need to install anything else on your server.

### Configuration

1. Edit the `jboss_wildfly.d/conf.yaml` file, in the `conf.d/` folder at the root of your
   Agent's configuration directory to start collecting your jboss or wildfly application server's
   performance data. See the [sample jboss_wildfly.d/conf.yaml][3] for all available configuration options.

   This check has a limit of 350 metrics per instance. The number of returned metrics is indicated in the info page.
   You can specify the metrics you are interested in by editing the configuration below. 
   To learn how to customize the metrics to collect visit the [JMX Checks documentation][4] for more detailed instructions.
   If you need to monitor more metrics, please send us an email at support@datadoghq.com

2. [Restart the Agent][5]

### Validation

[Run the Agent's `status` subcommand][6] and look for `jboss_wildfly` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Service Checks

JBoss/Wildfly does not include any service checks.

### Events

JBoss/Wildfly does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][8].


[1]: https://developers.redhat.com/products/eap/overview/
[2]: http://wildfly.org/
[3]: https://github.com/DataDog/integrations-core/blob/master/jboss_wildfly/datadog_checks/jboss_wildfly/data/conf.yaml.example
[4]: https://docs.datadoghq.com/integrations/java/
[5]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[6]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/jboss_wildfly/metadata.csv
[8]: https://docs.datadoghq.com/help/
