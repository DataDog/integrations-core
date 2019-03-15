# Linux_proc_extras Integration

## Overview
Get metrics from linux_proc_extras service in real time to:

* Visualize and monitor linux_proc_extras states
* Be notified about linux_proc_extras failovers and events.

## Setup
### Installation

The Linux_proc_extras check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your servers.

### Configuration

Edit the `linux_proc_extras.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][2]. See the [sample linux_proc_extras.d/conf.yaml][3] for all available configuration options.

### Validation

[Run the Agent's `status` subcommand][4] and look for `linux_proc_extras` under the Checks section.

## Data Collected
### Metrics
The Linux proc extras check does not include any metrics.

### Events
The Linux proc extras check does not include any events.

### Service Checks
The Linux proc extras check does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][5].

[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
[3]: https://github.com/DataDog/integrations-core/blob/master/linux_proc_extras/datadog_checks/linux_proc_extras/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://docs.datadoghq.com/help
