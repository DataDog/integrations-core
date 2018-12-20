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

2. [Restart the Agent][3]

### Validation

[Run the Agent's `status` subcommand][4] and look for `ibm_was` under the Checks section.

## Data Collected

### Metrics

Ibm_was does not include any metrics.

### Service Checks

Ibm_was does not include any service checks.

### Events

Ibm_was does not include any events.

## Troubleshooting

Need help? Contact [Datadog Support][5].

[1]: **LINK_TO_INTEGERATION_SITE**
[2]: https://github.com/DataDog/integrations-core/blob/master/ibm_was/datadog_checks/ibm_was/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://docs.datadoghq.com/help/
