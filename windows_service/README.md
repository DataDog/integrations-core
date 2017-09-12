# Agent Check: Windows Service

## Overview

This check monitors the state of any Windows Service and submits a service check to Datadog.

## Setup
### Installation

The Windows Service check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Windows hosts.

### Configuration

Create a file `windows_service.yaml` in the Agent's `conf.d` directory:

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

You must provide service names as they appear in services.msc's properties field (e.g. wmiApSrv), NOT the display name (e.g. WMI Performance Adapter).

Restart the Agent to start monitoring the services and sending service checks to Datadog.

### Validation

See the info page in the Agent Manager and look for `windows_service` under the Checks section:

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
See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/windows_service/metadata.csv) for a list of metrics provided by this integration.

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

If you have any questions about Datadog or a use case our [Docs](https://docs.datadoghq.com/) didn’t mention, we’d love to help! Here’s how you can reach out to us:

### Visit the Knowledge Base

Learn more about what you can do in Datadog on the [Support Knowledge Base](https://datadog.zendesk.com/agent/).

### Web Support

Messages in the [event stream](https://app.datadoghq.com/event/stream) containing **@support-datadog** will reach our Support Team. This is a convenient channel for referencing graph snapshots or a particular event. In addition, we have a livechat service available during the day (EST) from any page within the app.

### By Email

You can also contact our Support Team via email at [support@datadoghq.com](mailto:support@datadoghq.com).

### Over Slack

Reach out to our team and other Datadog users on [Slack](http://chat.datadoghq.com/).

## Further Reading
See our [series of blog posts](https://www.datadoghq.com/blog/monitoring-windows-server-2012) about monitoring Windows Server 2012 with Datadog.
