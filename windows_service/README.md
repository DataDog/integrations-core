# Agent Check: Windows Service

## Overview

This check monitors the state of any Windows Service and submits a service check to Datadog.

## Setup

### Installation

The Windows Service check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your Windows hosts.

### Configuration

Edit the `windows_service.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][2]. See the [sample windows_service.d/conf.yaml][3] for all available configuration options:

```yaml
init_config:

instances:
  ## @param services  - list of strings - required
  ## List of services to monitor e.g. Dnscache, wmiApSrv, etc.
  ##
  ## If any service is set to `ALL`, all services registered with the SCM are monitored.
  ##
  ## This matches all services starting with service, as if service.* is configured.
  ## For an exact match, use ^service$
  #
  - services:
      - "<SERVICE_NAME_1>"
      - "<SERVICE_NAME_2>"
  ## @param tags - list of strings following the pattern: "key:value" - optional
  ## List of tags to attach to every service check emitted by this integration.
  ##
  ## Learn more about tagging at https://docs.datadoghq.com/tagging
  #
  #  tags:
  #    - <KEY_1>:<VALUE_1>
  #    - <KEY_2>:<VALUE_2>
```

Provide service names as they appear in the `services.msc` properties field (e.g. `wmiApSrv`), **NOT** the display name (e.g. `WMI Performance Adapter`). For names with spaces: enclose the whole name in double quotation marks (e.g. "Bonjour Service"). **Note**: Spaces are replaced by underscores in Datadog.

[Restart the Agent][4] to start monitoring the services and sending service checks to Datadog.

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

**windows_service.state**:
The Agent submits this service check for each Windows service configured in `services`, tagging the service check with 'service:<service_name>'. The service check takes on the following statuses depending on Windows status:

| Windows status   | windows_service.state |
| ---------------- | --------------------- |
| Stopped          | CRITICAL              |
| Start Pending    | WARNING               |
| Stop Pending     | WARNING               |
| Running          | OK                    |
| Continue Pending | WARNING               |
| Pause Pending    | WARNING               |
| Paused           | WARNING               |
| Unknown          | UNKNOWN               |

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
[5]: https://docs.datadoghq.com/developers/metrics/custom_metrics
[6]: https://docs.datadoghq.com/account_management/billing/custom_metrics
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://docs.datadoghq.com/help
[9]: https://www.datadoghq.com/blog/monitoring-windows-server-2012
[10]: https://www.datadoghq.com/blog/collect-windows-server-2012-metrics
[11]: https://www.datadoghq.com/blog/windows-server-monitoring
