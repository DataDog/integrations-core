# Agent Check: System Core

![System Core][1]

## Overview

This check collects the number of CPU cores on a host and CPU times, such as `system`, `user`, `idle`, etc.

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

Depending on the platform, the check may collect other CPU time metrics, such as `system.core.interrupt` on Windows, `system.core.iowait` on Linux, etc.

### Events

The System Core check does not include any events.

### Service Checks

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].

### Windows and high numbers of processors

Due to [the way Windows splits processors into groups][10], metrics
for individual cores collected from this integration may have invalid
values for Windows hosts with high (> 64) numbers of cores for a
portion of the cores.

Note that `*.total` metrics should still reflect accurate values in
the above situation, and only per-core metrics are affected.

Datadog recommends that users with this type of configuration set up the
[Windows Performance Counters integration][11] to track counters
inside the `Processor Information`. This enables users to get accurate per-core
metrics.

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/system_core/images/syscoredash.png
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/system_core/datadog_checks/system_core/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/system_core/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/system_core/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://docs.microsoft.com/en-us/windows/win32/procthread/processor-groups
[11]: https://docs.datadoghq.com/integrations/windows_performance_counters/
