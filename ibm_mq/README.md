# Agent Check: IBM MQ

## Overview

This check monitors [Ibm_mq][1].

## Setup

### Installation

The Ibm_mq check is included in the [Datadog Agent][2] package. However, in order for it to work it needs to have an IBM MQ client installed on the box.

### Configuration

1. Edit the `ibm_mq.d/conf.yaml` file, in the `conf.d/` folder at the root of your
   Agent's configuration directory to start collecting your ibm_mq performance data.
   See the [sample ibm_mq.d/conf.yaml][3] for all available configuration options.

2. [Restart the Agent][4]

### Validation

[Run the Agent's `status` subcommand][5] and look for `ibm_mq` under the Checks section.

## Data Collected

### Metrics

Ibm_mq does not include any metrics.

### Service Checks

Ibm_mq does not include any service checks.

### Events

Ibm_mq does not include any events.

## Troubleshooting

Need help? Contact [Datadog Support][6].

[1]: https://www.ibm.com/products/mq
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://github.com/DataDog/integrations-core/blob/master/ibm_mq/datadog_checks/ibm_mq/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[5]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[6]: https://docs.datadoghq.com/help/
