# Agent Check: battery

## Overview

This check monitors battery health of MacOS and Windows laptops.

**Minimum Agent version:** 7.75.0

## Setup

### Installation

The Battery check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

The configuration is located in the `battery.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][1]. See the [sample battery.d/conf.yaml][4] for all available configuration options. When you are done editing the configuration file, [restart the Agent][5] to load the new configuration.

### Validation

[Run the Agent's `status` subcommand][6] and look for `battery` under the Checks section.

**Note**: If no battery is detected in the system, the check will not run.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The Battery check does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][3].

[1]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/help/
[4]: https://github.com/DataDog/datadog-agent/blob/main/cmd/agent/dist/conf.d/battery.d/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/configuration/agent-commands/#agent-information
[7]: https://github.com/DataDog/integrations-core/blob/master/battery/metadata.csv

