# Linux Proc Extras Integration

## Overview

Get metrics from linux_proc_extras service in real time to:

- Visualize and monitor linux_proc_extras states
- Be notified about linux_proc_extras failovers and events.

## Setup

### Installation

The Linux_proc_extras check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your servers.

### Configuration

Edit the `linux_proc_extras.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][2]. See the [sample linux_proc_extras.d/conf.yaml][3] for all available configuration options.

#### Metrics collection

The Linux Proc Extras check can potentially emit [custom metrics][4], which may impact your [billing][5].

### Validation

[Run the Agent's status subcommand][6] and look for `linux_proc_extras` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][8] for a list of metrics provided by this integration.

### Events

The Linux Proc Extras check does not include any events.

### Service Checks

The Linux Proc Extras check does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][7].

[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[3]: https://github.com/DataDog/integrations-core/blob/master/linux_proc_extras/datadog_checks/linux_proc_extras/data/conf.yaml.example
[4]: https://docs.datadoghq.com/developers/metrics/custom_metrics/
[5]: https://docs.datadoghq.com/account_management/billing/custom_metrics/
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://docs.datadoghq.com/help/
[8]: https://github.com/DataDog/integrations-core/blob/master/linux_proc_extras/metadata.csv
