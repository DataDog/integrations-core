# Agent Check: Windows Service

## Overview

This check monitors the state of any Windows Service and submits a service check to Datadog.

## Setup

### Installation

The Windows Service check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your Windows hosts.

### Configuration

1. Edit the `windows_service.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][2]. See the [sample windows_service.d/conf.yaml][3] for all available configuration options.

2. Provide service names as they appear in the `services.msc` properties field **NOT** the display name. For names with spaces, enclose the whole name in double quotation marks, for example: `"Windows Service"`. **Note**: Spaces are replaced by underscores in Datadog.

3. [Restart the Agent][4].

#### Metrics collection

The Windows Service check can potentially emit [custom metrics][5], which may impact your [billing][6].

### Validation

[Run the Agent's status subcommand][7] and look for `windows_service` under the Checks section.

## Data Collected

### Metrics

The Windows Service check does not include any metrics.

### Events

The Windows Service check does not include any events.

### Service Checks

See [service_checks.json][12] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][8].

## Further Reading

- [Monitoring Windows Server 2012][9]
- [How to collect Windows Server 2012 metrics][10]
- [Monitoring Windows Server 2012 with Datadog][11]

[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[3]: https://github.com/DataDog/integrations-core/blob/master/windows_service/datadog_checks/windows_service/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/developers/metrics/custom_metrics/
[6]: https://docs.datadoghq.com/account_management/billing/custom_metrics/
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://docs.datadoghq.com/help/
[9]: https://www.datadoghq.com/blog/monitoring-windows-server-2012
[10]: https://www.datadoghq.com/blog/collect-windows-server-2012-metrics
[11]: https://www.datadoghq.com/blog/windows-server-monitoring
[12]: https://github.com/DataDog/integrations-core/blob/master/windows_service/assets/service_checks.json
