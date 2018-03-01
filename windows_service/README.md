# Agent Check: Windows Service
{{< img src="integrations/winservices/windows-service.png" alt="Windows Service Event" responsive="true" popup="true">}}
## Overview

This check monitors the state of any Windows Service and submits a service check to Datadog.

## Setup
### Installation

The Windows Service check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Windows hosts.

### Configuration

Create a file `windows_service.yaml` in the Agent's `conf.d` directory. See the [sample windows_service.yaml](https://github.com/DataDog/integrations-core/blob/master/windows_service/conf.yaml.example) for all available configuration options:

```
init_config:

instances:
  - host: . # dot means localhost
#   username: <REMOTESERVER>\<REMOTEUSER> # if 'host' is a remote host
#   password: <PASSWORD>

# list at least one service to monitor
    services:
#     - wmiApSrv
```

Provide service names as they appear in services.msc's properties field (e.g. `wmiApSrv`), **NOT** the display name (e.g. `WMI Performance Adapter`). For names with spaces: enclose the whole name in double quotation marks (e.g. "Bonjour Service").  
Note: spaces are replaced by underscores in Datadog.

[Restart the Agent](https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent) to start monitoring the services and sending service checks to Datadog.

### Validation

[Run the Agent's `status` subcommand](https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information) and look for `windows_service` under the Checks section:

```
  Checks
  ======
    [...]

    windows_service
    -------
      - instance #0 [OK]
      - Collected 0 metrics, 0 events & 1 service check

    [...]
```

## Compatibility

The Windows Service check is compatible with all Windows platforms.

## Data Collected
### Metrics

The Windows Service check does not include any metrics at this time.

### Events
The Windows Service check does not include any event at this time.

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
Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading

* [Monitoring Windows Server 2012](https://www.datadoghq.com/blog/monitoring-windows-server-2012/)
* [How to collect Windows Server 2012 metrics](https://www.datadoghq.com/blog/collect-windows-server-2012-metrics/)
* [Monitoring Windows Server 2012 with Datadog](https://www.datadoghq.com/blog/windows-server-monitoring/)
