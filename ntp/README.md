# NTP check

## Overview

The Network Time Protocol (NTP) integration is enabled by default and reports the time offset from an ntp server every 15 minutes. When the local Agent's time is more than 15 seconds off from the Datadog service and other hosts you are monitoring, you may experience:

- Incorrect alert triggers
- Metric delays
- Gaps in graphs of metrics

By default, the check detects which cloud provider the Agent is running on and uses the private
NTP server of that cloud provider, if available. If no cloud provider is detected, the agent will
default to the NTP servers below:

- `0.datadog.pool.ntp.org`
- `1.datadog.pool.ntp.org`
- `2.datadog.pool.ntp.org`
- `3.datadog.pool.ntp.org`

**Note:** NTP requests do not support proxy settings.

## Setup

### Installation

The NTP check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your servers.

### Configuration

The Agent enables the NTP check by default. To configure the check yourself, edit the file `ntp.d/conf.yaml` in the `conf.d/` folder at the root of your [Agent's configuration directory][2]. See the [sample ntp.d/conf.yaml][3] for all available configuration options.

**Note**: If you edit the Datadog-NTP check configuration file, [restart the Agent][4] to effect any configuration changes.

### Validation

[Run the Agent's `status` subcommand][5] and look for `ntp` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][6] for a list of metrics provided by this check.

### Events

The NTP check does not include any events.

### Service Checks

See [service_checks.json][7] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][8].

[1]: https://app.datadoghq.com/account/settings/agent/latest
[2]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[3]: https://github.com/DataDog/datadog-agent/blob/master/cmd/agent/dist/conf.d/ntp.d/conf.yaml.default
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/ntp/metadata.csv
[7]: https://github.com/DataDog/integrations-core/blob/master/ntp/assets/service_checks.json
[8]: https://docs.datadoghq.com/help/
