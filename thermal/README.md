# Thermal Integration

## Overview

This check monitors hardware temperatures and thermal constraints on Windows and macOS hosts.

On Windows, the check collects the temperature and passive performance limit for each thermal zone exposed by the operating system. On macOS, it collects available CPU, GPU, SSD, and battery temperatures from AppleSMC, along with the system thermal pressure level.

Sensors that are unavailable on a host are omitted rather than reported as zero. The set of available metrics can vary by hardware model.

**Minimum Agent version:** 7.82.0 on Windows and 7.84.0 on macOS.

## Setup

### Installation

The Thermal integration is included in the [Datadog Agent][1] package. No additional installation is needed.

### Configuration

The Thermal check is not enabled by default.

1. Copy the [sample `thermal.d/conf.yaml`][2] to `thermal.d/conf.yaml` in the `conf.d` folder at the root of the Agent's [configuration directory][3]. No check-specific options are required:

   ```yaml
   init_config:

   instances:
     - {}
   ```

2. [Restart the Agent][4].

### Validation

[Run the Agent's status subcommand][5] and look for `thermal` under the **Checks** section.

On Windows hosts without thermal zones, such as some virtual machines, the check runs without submitting metrics. On macOS, the check submits only the sensors exposed by the hardware.

## Data Collected

### Metrics

See [metadata.csv][6] for a list of metrics provided by this integration.

### Tags

On Windows, each metric is tagged with `thermal_zone:<instance>`, where `<instance>` identifies the thermal zone reported by Windows.

On macOS, hardware temperature metrics have the `macos` and `smc` tags and a tag identifying the sensor type: `cpu`, `gpu`, `ssd`, or `battery`. The `system.thermal.pressure_level` metric has the `macos` tag and a `pressure_level:<name>` tag. The possible pressure levels are:

| Value | Tag | Description |
| --- | --- | --- |
| `0` | `pressure_level:nominal` | No thermal constraint. |
| `1` | `pressure_level:moderate` | Mild thermal pressure. |
| `2` | `pressure_level:heavy` | Substantial thermal pressure. |
| `3` | `pressure_level:trapping` | Severe thermal pressure that requires the system to limit work. |
| `4` | `pressure_level:sleeping` | Critical thermal pressure that may force the system to sleep. |

The check uses `pressure_level:unknown` if macOS returns an unrecognized pressure value.

### Events

The Thermal integration does not include any events.

### Service Checks

The Thermal integration does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][7] with an [Agent Flare][8].

[1]: https://app.datadoghq.com/account/settings/agent/latest
[2]: https://github.com/DataDog/datadog-agent/blob/main/cmd/agent/dist/conf.d/thermal.d/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/configuration/agent-configuration-files/#agent-configuration-directory
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#restart-the-agent
[5]: https://docs.datadoghq.com/agent/configuration/agent-commands/#agent-information
[6]: https://github.com/DataDog/integrations-core/blob/master/thermal/metadata.csv
[7]: https://docs.datadoghq.com/help/
[8]: https://docs.datadoghq.com/agent/troubleshooting/send_a_flare/?tab=agentv6v7
