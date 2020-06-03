# Agent Check: Windows Event Log

## Overview

The Win 32 event log check watches for Windows Event Logs and forwards them to Datadog. Enable this check to:

- Track system and application events in Datadog.
- Correlate system and application events with the rest of your application.

## Setup

### Installation

The Windows Event Log check is included in the [Datadog Agent][1] package. There is no additional installation required.

### Configuration

1. Edit the `win32_event_log.d/conf.yaml` in the `conf.d/` folder at the root of your [Agent's configuration directory][2]. See the [sample win32_event_log.d/conf.yaml][3] for all available configuration options.

2. [Restart the Agent][4] to start sending Windows events to Datadog.

### Log collection

To collect logs from specific Windows events, add the channels to the `conf.d/win32_event_log.d/conf.yaml` file manually, or via the Datadog Agent Manager.

To see the channel list, run the following command in a PowerShell:

```powershell
Get-WinEvent -ListLog *
```

To see the most active channels, run the following command in a PowerShell:

```powershell
Get-WinEvent -ListLog * | sort RecordCount -Descending
```

This command displays channels in the format `LogMode MaximumSizeInBytes RecordCount LogName`. Example response:

```text
LogMode MaximumSizeInBytes RecordCount LogName
Circular 134217728 249896 Security
```

The value under the column `LogName` is the name of the channel. In the above example, the channel name is `Security`.

Then add the channels in your `win32_event_log.d/conf.yaml` configuration file:

```yaml
logs:
  - type: windows_event
    channel_path: "<CHANNEL_1>"
    source: "<CHANNEL_1>"
    service: myservice

  - type: windows_event
    channel_path: "<CHANNEL_2>"
    source: "<CHANNEL_2>"
    service: myservice
```

Edit the `<CHANNEL_X>` parameters with the Windows channel name you want to collect events from.
Set the corresponding `source` parameter to the same channel name to benefit from the [integration automatic processing pipeline][5].

Finally, [restart the Agent][4].

**Note**: For the Security logs channel, add your Datadog Agent user to the `Event Log Readers` user group.

### Filters

Use the Windows Event Viewer GUI to list all the event logs available for capture with this integration.

To determine the exact values, set your filters to use the following PowerShell command:

```text
Get-WmiObject -Class Win32_NTLogEvent
```

For instance, to see the latest event logged in the `Security` LogFile, use:

```text
Get-WmiObject -Class Win32_NTLogEvent -Filter "LogFile='Security'" | select -First 1
```

The values listed in the output of the command can be set in `win32_event_log.d/conf.yaml` to capture the same kind of events.

<div class="alert alert-info">
The information given by the  <code> Get-EventLog</code> PowerShell command or the Windows Event ViewerGUI may slightly differ from <code>Get-WmiObject</code>.<br>
Double-check your filters' values with <code>Get-WmiObject</code> if the integration doesn't capture the events you set up.
</div>

1. Configure one or more filters for the event log. A filter allows you to choose what log events you want to get into Datadog.

    Filter on the following properties:

      - type: Warning, Error, Information
      - log_file: Application, System, Setup, Security
      - source_name: Any available source name
      - user: Any valid user name

    For each filter, add an instance in the configuration file at `win32_event_log.d/conf.yaml`.

    Some example filters:

   ```yaml
   instances:
     # The following captures errors and warnings from SQL Server which
     # puts all events under the MSSQLSERVER source and tag them with #sqlserver.
     - tags:
         - sqlserver
       type:
         - Warning
         - Error
       log_file:
         - Application
       source_name:
         - MSSQLSERVER

     # This instance captures all system errors and tags them with #system.
     - tags:
         - system
       type:
         - Error
       log_file:
         - System
   ```

2. [Restart the Agent][4] using the Agent Manager (or restart the service)

### Validation

Check the info page in the Datadog Agent Manager or run the [Agent's `status` subcommand][6] and look for `win32_event_log` under the Checks section. It should display a section similar to the following:

```shell
Checks
======

  [...]

  win32_event_log
  ---------------
      - instance #0 [OK]
      - Collected 0 metrics, 2 events & 1 service check
```

## Data Collected

### Metrics

The Win32 Event log check does not include any metrics.

### Events

All Windows Event are forwarded to your Datadog application.

### Service Checks

The Win32 Event log check does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][7].

## Further Reading

### Documentation

- [How to add event log files to the `Win32_NTLogEvent` WMI class][8]

### Blog

- [Monitoring Windows Server 2012][9]
- [How to collect Windows Server 2012 metrics][10]
- [Monitoring Windows Server 2012 with Datadog][11]

[1]: https://app.datadoghq.com/account/settings#agent/windows
[2]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[3]: https://github.com/DataDog/integrations-core/blob/master/win32_event_log/datadog_checks/win32_event_log/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/logs/processing/pipelines/#integration-pipelines
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://docs.datadoghq.com/help/
[8]: https://docs.datadoghq.com/integrations/faq/how-to-add-event-log-files-to-the-win32-ntlogevent-wmi-class/
[9]: https://www.datadoghq.com/blog/monitoring-windows-server-2012
[10]: https://www.datadoghq.com/blog/collect-windows-server-2012-metrics
[11]: https://www.datadoghq.com/blog/windows-server-monitoring
