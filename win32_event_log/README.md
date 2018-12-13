# Agent Check: Windows Event Log

## Overview

This check watches for events in the Windows Event Log and forwards them to Datadog.

## Setup
### Installation

The Windows Event Log check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your Windows hosts.

### Configuration

Edit the `win32_event_log.d/conf.yaml` in the `conf.d/` folder at the root of your [Agent's configuration directory][2]. See the [sample win32_event_log.d/conf.yaml][3] for all available configuration options:

```
init_config:

instances:
  - host: localhost
```

This minimal file will capture all events from localhost, but you can configure the check to only collect certain kinds of events. See the [example check configuration][3] for a comprehensive list and description of options that allow you to do that.

[Restart the Agent][4] to start sending Windows events to Datadog.

### Validation

[Run the Agent's `status` subcommand][5] and look for `win32_event_log` under the Checks section.

## Data Collected
### Metrics
The Win32 Event log check does not include any metrics at this time.

### Events
All Windows Event are forwarded to your Datadog application

### Service Checks
The Win32 Event log check does not include any service checks at this time.

## Troubleshooting

Need help? Contact [Datadog Support][6].

## Further Reading
### Knowledge base

* [How to add event log files to the `Win32_NTLogEvent` WMI class][7]

### Blog

* [Monitoring Windows Server 2012][8]
* [How to collect Windows Server 2012 metrics][9]
* [Monitoring Windows Server 2012 with Datadog][10]


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
[3]: https://github.com/DataDog/integrations-core/blob/master/win32_event_log/datadog_checks/win32_event_log/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[5]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[6]: https://docs.datadoghq.com/help
[7]: https://docs.datadoghq.com/integrations/faq/how-to-add-event-log-files-to-the-win32-ntlogevent-wmi-class
[8]: https://www.datadoghq.com/blog/monitoring-windows-server-2012
[9]: https://www.datadoghq.com/blog/collect-windows-server-2012-metrics
[10]: https://www.datadoghq.com/blog/windows-server-monitoring
