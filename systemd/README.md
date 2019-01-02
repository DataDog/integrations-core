# Agent Check: Systemd

## Overview

This check monitors [Systemd][1] and the units it manages through the Datadog Agent.

## Setup

### Installation

The Systemd check is included in the [Datadog Agent][2] package. No additional installation is needed on your server.

### Configuration

1. Edit the `systemd.d/conf.yaml` file, in the `conf.d/` folder at the root of your
   Agent's configuration directory to start collecting your systemd performance data.
   See the [sample systemd.d/conf.yaml][3] for all available configuration options.

2. [Restart the Agent][4].

### Validation

[Run the Agent's status subcommand][5] and look for `systemd` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][6] for a list of metrics provided by this check.

### Service Checks

**systemd.can_connect**:  

Returns `OK` if systemd is reachable, `CRITICAL` otherwise.

**systemd.system_state**:

Returns `OK` if systemd's system state is running, `CRITICAL` if degraded, maintenance or stopping, `UNKNOWN` if initializing, starting or other.

**systemd.unit.active_state**:
Returns `OK` if the unit active state is active, `CRITICAL` if inactive, deactivating or failed, `UNKNOWN` if activating or other.


### Events

The Agent_metrics check does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][7].

[1]: https://www.freedesktop.org/wiki/Software/systemd/
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://github.com/DataDog/datadog-agent/blob/master/cmd/agent/dist/conf.d/systemd.d/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[5]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/systemd/metadata.csv
[7]: https://docs.datadoghq.com/help/
