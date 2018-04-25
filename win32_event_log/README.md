# Agent Check: Windows Event Log

## Overview

This check watches for events in the Windows Event Log and forwards them to Datadog.

## Setup
### Installation

The Windows Event Log check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Windows hosts.

### Configuration

Create a file `win32_event_log.yaml` in the Agent's `conf.d` directory. See the [sample win32_event_log.yaml](https://github.com/DataDog/integrations-core/blob/master/win32_event_log/conf.yaml.example) for all available configuration options:

```
init_config:

instances:
  - host: localhost
```

This minimal file will capture all events from localhost, but you can configure the check to only collect certain kinds of events. See the [example check configuration](https://github.com/DataDog/integrations-core/blob/master/win32_event_log/conf.yaml.example) for a comprehensive list and description of options that allow you to do that.

[Restart the Agent](https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent) to start sending Windows events to Datadog.

### Validation

[Run the Agent's `status` subcommand](https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information) and look for `win32_event_log` under the Checks section.

## Compatibility

The win32_event_log check is compatible with all Windows platforms.

## Data Collected
### Metrics
The Win32 Event log check does not include any metric at this time.

### Events
All Windows Event are forwarded to your Datadog application

### Service Checks
The Win32 Event log check does not include any service check at this time.

## Troubleshooting

Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading
### Knowledge base

* [How to add event log files to the `Win32_NTLogEvent` WMI class](https://docs.datadoghq.com/integrations/faq/how-to-add-event-log-files-to-the-win32-ntlogevent-wmi-class/)

### Blog

* [Monitoring Windows Server 2012](https://www.datadoghq.com/blog/monitoring-windows-server-2012/)
* [How to collect Windows Server 2012 metrics](https://www.datadoghq.com/blog/collect-windows-server-2012-metrics/)
* [Monitoring Windows Server 2012 with Datadog](https://www.datadoghq.com/blog/windows-server-monitoring/)
