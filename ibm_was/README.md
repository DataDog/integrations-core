# Agent Check: Ibm_was

## Overview

This check monitors [Ibm_was][1].

## Setup

### Installation

The Ibm_was check is included in the [Datadog Agent][2] package, so you do not
need to install anything else on your server.

### Configuration

1. Edit the `ibm_was.d/conf.yaml` file, in the `conf.d/` folder at the root of your
   Agent's configuration directory to start collecting your ibm_was performance data.
   See the [sample ibm_was.d/conf.yaml][2] for all available configuration options.

   This check has a limit of 350 metrics per instance. The number of returned metrics is indicated in the info page.
   You can specify the metrics you are interested in by editing the configuration below. 
   To learn how to customize the metrics to collect visit the [JMX Checks documentation][3] for more detailed instructions.
   If you need to monitor more metrics, please send us an email at support@datadoghq.com

2. [Restart the Agent][4]

### Validation

[Run the Agent's `status` subcommand][5] and look for `ibm_was` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][6] for a list of metrics provided by this check.

### Service Checks

Ibm_was does not include any service checks.

### Events

Ibm_was does not include any events.

## Troubleshooting

Need help? Contact [Datadog Support][7].


[1]: **LINK_TO_INTEGERATION_SITE**
[2]: https://github.com/DataDog/integrations-core/blob/master/ibm_was/datadog_checks/ibm_was/data/conf.yaml.example
[3]: https://docs.datadoghq.com/integrations/java/
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[5]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/ibm_was/metadata.csv
[7]: https://docs.datadoghq.com/help/
