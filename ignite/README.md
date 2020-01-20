# Agent Check: Ignite

## Overview

This check monitors [Ignite][1].

## Setup

### Installation

The ignite check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `ignite.d/conf.yaml` file, in the `conf.d/` folder at the root of your
   Agent's configuration directory to start collecting your ignite performance data.
   See the [sample ignite.d/conf.yaml][2] for all available configuration options.

   This check has a limit of 350 metrics per instance. The number of returned metrics is indicated in the info page.
   You can specify the metrics you are interested in by editing the configuration below.
   To learn how to customize the metrics to collect visit the [JMX Checks documentation][3] for more detailed instructions.
   If you need to monitor more metrics, contact [Datadog support][4].

2. [Restart the Agent][5]

### Validation

[Run the Agent's `status` subcommand][6] and look for `ignite` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Service Checks

**ignite.can_connect**:<br>
Returns `CRITICAL` if the Agent is unable to connect to and collect metrics from the monitored Ignite instance, otherwise returns `OK`.

### Events

The Ignite integration does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][4].


[1]: https://ignite.apache.org/
[2]: https://github.com/DataDog/integrations-core/blob/master/ignite/datadog_checks/ignite/data/conf.yaml.example
[3]: https://docs.datadoghq.com/integrations/java
[4]: https://docs.datadoghq.com/help
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/ignite/metadata.csv
