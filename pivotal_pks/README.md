# Agent Check: Pivotal_pks

## Overview

This check monitors [Pivotal_pks][1].

## Setup

### Installation

The Pivotal_pks check is included in the [Datadog Agent][2] package, so you do not
need to install anything else on your server.

### Configuration

1. Edit the `pivotal_pks.d/conf.yaml` file, in the `conf.d/` folder at the root of your
   Agent's configuration directory to start collecting your pivotal_pks performance data.
   See the [sample pivotal_pks.d/conf.yaml][3] for all available configuration options.

2. [Restart the Agent][4]

### Validation

[Run the Agent's `status` subcommand][5] and look for `pivotal_pks` under the Checks section.

## Data Collected

### Metrics

Pivotal_pks does not include any metrics.

### Service Checks

Pivotal_pks does not include any service checks.

### Events

Pivotal_pks does not include any events.

## Troubleshooting

Need help? Contact [Datadog Support][6].

[1]: **LINK_TO_INTEGERATION_SITE**
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://github.com/DataDog/integrations-core/blob/master/pivotal_pks/datadog_checks/pivotal_pks/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[5]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[6]: https://docs.datadoghq.com/help/
