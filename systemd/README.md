# Agent Check: Systemd

## Overview

This check monitors [Systemd][1] through the Datadog Agent.

## Setup

### Installation

The Systemd check is included in the [Datadog Agent][2] package. No additional installation is needed on your server.

### Configuration

1. Edit the `systemd.d/conf.yaml` file, in the `conf.d/` folder at the root of your
   Agent's configuration directory to start collecting your systemd performance data.
   See the [sample systemd.d/conf.yaml][2] for all available configuration options.

2. [Restart the Agent][3].

### Validation

[Run the Agent's status subcommand][4] and look for `systemd` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][5] for a list of metrics provided by this check.

### Service Checks

**systemd.unit.active**:  
Returns `CRITICAL` if the unit's state is 'inactive' or 'failed', `WARN` if it's 'deactivating', otherwise returns `OK`.

### Events

The Systemd check emits an event to Datadog each time a unit in the configuration file changes state.

## Troubleshooting

Need help? Contact [Datadog support][5].

[1]: https://www.freedesktop.org/wiki/Software/systemd/
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://github.com/DataDog/integrations-core/blob/master/systemd/datadog_checks/systemd/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[5]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/systemd/metadata.csv
[7]: https://docs.datadoghq.com/help/
