# Dotnetclr Integration

## Overview

Get metrics from the .NET CLR service in real time to:

- Visualize and monitor .NET CLR states.
- Be notified about .NET CLR failovers and events.

## Setup

### Installation

The .NET CLR check is included in the [Datadog Agent][2] package. No additional installation is needed on your server.

### Configuration

1. Edit the `dotnetclr.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][3] to start collecting your .NET CLR performance data. See the [sample dotnetclr.d/conf.yaml][4] for all available configuration options.
2. [Restart the Agent][5].

## Validation

[Run the Agent's status subcommand][6] and look for `dotnetclr` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of all metrics provided by this integration.

### Service Checks

The .NET CLR check does not include any service checks.

### Events

The .NET CLR check does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][8].

[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/dotnetclr/datadog_checks/dotnetclr/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/dotnetclr/metadata.csv
[8]: https://docs.datadoghq.com/help/
