# Agent Check: Windows performance counters

## Overview

This check monitors [Windows performance counters][1] through the Datadog Agent.

**Note:** Agent version 7.33.0 is the minimum supported version.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The Windows performance counters check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `windows_performance_counters.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your windows_performance_counters performance data. See the [sample windows_performance_counters.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `windows_performance_counters` under the Checks section.

## Data Collected

### Metrics

All metrics collected by the Windows performance counters check are forwarded to Datadog as [custom metrics][7], which may impact your [billing][8].

### Events

The Windows performance counters integration does not include any events.

### Service Checks

See [service_checks.json][9] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][10].

## Further Reading

Additional helpful documentation, links, and articles:

- [Monitor Windows Performance Counters with Datadog][11]

[1]: https://docs.microsoft.com/en-us/windows/win32/perfctrs/about-performance-counters
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/windows_performance_counters/datadog_checks/windows_performance_counters/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://docs.datadoghq.com/developers/metrics/custom_metrics/
[8]: https://docs.datadoghq.com/account_management/billing/custom_metrics/
[9]: https://github.com/DataDog/integrations-core/blob/master/windows_performance_counters/assets/service_checks.json
[10]: https://docs.datadoghq.com/help/
[11]: https://www.datadoghq.com/blog/windows-performance-counters-datadog/
