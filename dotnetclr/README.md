# Dotnetclr Integration

## Overview

Get metrics from the .NET CLR service in real time to:

- Visualize and monitor .NET CLR states.
- Be notified about .NET CLR failovers and events.

## Setup

### Installation

The .NET CLR check is included in the [Datadog Agent][1] package. No additional installation is needed on your server.

### Configuration

1. Edit the `dotnetclr.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][2] to start collecting your .NET CLR performance data. See the [sample dotnetclr.d/conf.yaml][3] for all available configuration options.
2. [Restart the Agent][4].

**Note**: Versions 1.10.0 or later of this check use a new implementation for metric collection, which requires Python 3. For hosts that are unable to use Python 3, or if you would like to use a legacy version of this check, refer to the following [config][8].

## Validation

[Run the Agent's status subcommand][5] and look for `dotnetclr` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][6] for a list of all metrics provided by this integration.

### Service Checks

The .NET CLR check does not include any service checks.

### Events

The .NET CLR check does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][7].

[1]: https://app.datadoghq.com/account/settings/agent/latest
[2]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[3]: https://github.com/DataDog/integrations-core/blob/master/dotnetclr/datadog_checks/dotnetclr/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/dotnetclr/metadata.csv
[7]: https://docs.datadoghq.com/help/
[8]: https://github.com/DataDog/integrations-core/blob/7.33.x/dotnetclr/datadog_checks/dotnetclr/data/conf.yaml.example
