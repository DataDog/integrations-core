# Agent Check: hive

## Overview

This check monitors [hive][1].

## Setup

### Installation

The hive check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `hive.d/conf.yaml` file, in the `conf.d/` folder at the root of your
   Agent's configuration directory to start collecting your hive performance data.
   See the [sample hive.d/conf.yaml][2] for all available configuration options.

   This check has a limit of 350 metrics per instance. The number of returned metrics is indicated in the info page.
   You can specify the metrics you are interested in by editing the configuration below.
   To learn how to customize the metrics to collect visit the [JMX Checks documentation][3] for more detailed instructions.
   If you need to monitor more metrics, please send us an email at support@datadoghq.com

2. [Restart the Agent][4]

### Validation

[Run the Agent's `status` subcommand][5] and look for `hive` under the Checks section.

## Data Collected

### Metrics

hive does not include any metrics.

### Service Checks

hive does not include any service checks.

### Events

hive does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][6].


[1]: **LINK_TO_INTEGERATION_SITE**
[2]: https://github.com/DataDog/integrations-core/blob/master/hive/datadog_checks/hive/data/conf.yaml.example
[3]: https://docs.datadoghq.com/integrations/java
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[6]: https://docs.datadoghq.com/help
