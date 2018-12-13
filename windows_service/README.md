# Agent Check: Windows Service
## Overview

This check monitors the state of any Windows Service and submits a service check to Datadog.

## Setup

### Installation

The Windows Service check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your Windows hosts.

### Configuration

Edit the `windows_service.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][2]. See the [sample windows_service.d/conf.yaml][3] for all available configuration options:

```
init_config:

instances:
  ## @param services  - list of strings - required
  ## List of services to monitor e.g. Dnscache, wmiApSrv, etc.
  ##
  ## If any service is set to `ALL`, all services registered with the SCM will be monitored.
  ##
  ## The services are treated as regular expressions to allow for advanced matching. So if
  ## you say `Event.*`, the check will monitor any service starting with the word `Event`.
  #
  - services:
      - <SERVICE_NAME_1>
      - <SERVICE_NAME_2>

  ## @param tags  - list of key:value element - optional
  ## List of tags to attach to every service check emitted by this integration.
  ##
  ## Learn more about tagging at https://docs.datadoghq.com/tagging
  #
  #  tags:
  #    - <KEY_1>:<VALUE_1>
  #    - <KEY_2>:<VALUE_2>
```

Provide service names as they appear in services.msc's properties field (e.g. `wmiApSrv`), **NOT** the display name (e.g. `WMI Performance Adapter`). For names with spaces: enclose the whole name in double quotation marks (e.g. "Bonjour Service").
Note: spaces are replaced by underscores in Datadog.

[Restart the Agent][4] to start monitoring the services and sending service checks to Datadog.

### Validation

[Run the Agent's `status` subcommand][5] and look for `windows_service` under the Checks section.

## Data Collected
### Metrics

The Windows Service check does not include any metrics at this time.

### Events
The Windows Service check does not include any events at this time.

### Service Checks
**windows_service.state**:

The Agent submits this service check for each Windows service configured in `services`, tagging the service check with 'service:<service_name>'. The service check takes on the following statuses depending on Windows status:

|Windows status|windows_service.state|
|---|---|
|Stopped|CRITICAL|
|Start Pending|WARNING|
|Stop Pending|WARNING|
|Running|OK|
|Continue Pending|WARNING|
|Pause Pending|WARNING|
|Paused|WARNING|
|Unknown|UNKNOWN|

## Troubleshooting
Need help? Contact [Datadog Support][6].

## Further Reading

* [Monitoring Windows Server 2012][7]
* [How to collect Windows Server 2012 metrics][8]
* [Monitoring Windows Server 2012 with Datadog][9]


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
[3]: https://github.com/DataDog/integrations-core/blob/master/windows_service/datadog_checks/windows_service/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[5]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[6]: https://docs.datadoghq.com/help
[7]: https://www.datadoghq.com/blog/monitoring-windows-server-2012
[8]: https://www.datadoghq.com/blog/collect-windows-server-2012-metrics
[9]: https://www.datadoghq.com/blog/windows-server-monitoring
