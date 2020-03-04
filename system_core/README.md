# Agent Check: System Core

![System Core][1]

## Overview

This check collects the number of CPU cores on a host and CPU times (i.e. system, user, idle, etc).

## Setup

### Installation

The System Core check is included in the [Datadog Agent][2] package. No additional installation is needed on your server.

### Configuration

1. Edit the `system_core.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][3]. See the [sample system_core.d/conf.yaml][4] for all available configuration options. **Note**: At least one entry is required under `instances` to enable the check, for example:

   ```yaml
   init_config:

   instances:
     - foo: bar
   ```

2. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `system_core` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this check.

Depending on the platform, the check may collect other CPU time metrics, e.g. `system.core.interrupt` on Windows, `system.core.iowait` on Linux, etc.

### Events

The System Core check does not include any events.

### Service Checks

The System Core check does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][8].

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/system_core/images/syscoredash.png
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/system_core/datadog_checks/system_core/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/system_core/metadata.csv
[8]: https://docs.datadoghq.com/help
