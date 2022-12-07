# Agent Check: Windows Event Log

## Overview

The Win32 event log check watches for Windows Event Logs and forwards them to Datadog. Enable this check to:

- Track system and application events in Datadog.
- Correlate system and application events with the rest of your application.

For more information, see the [Windows Event Logging documentation][13].

## Setup

### Installation

The Windows Event Log check is included in the [Datadog Agent][1] package. There is no additional installation required.

### Configuration

Windows Event logs can be collected as one or both of the following methods.
- As [Datadog Events][16]
- As [Datadog Logs][17]

Both methods are configured in `win32_event_log.d/conf.yaml` in the `conf.d/` folder at the root of your [Agent's configuration directory][2]. See the [sample win32_event_log.d/conf.yaml][3] for all available configuration options.


#### List Windows Event channels

First, identify the Windows Event Log channels you want to monitor. To see a list of channels, run the following command in PowerShell:

```powershell
Get-WinEvent -ListLog *
```

To see the most active channels, run the following command in PowerShell:

```powershell
Get-WinEvent -ListLog * | sort RecordCount -Descending
```

This command displays channels in the format `LogMode MaximumSizeInBytes RecordCount LogName`. Example response:

```text
LogMode  MaximumSizeInBytes RecordCount LogName 
Circular          134217728      249896 Security
Circular            5242880        2932 <CHANNEL_2>
```

The value under the column `LogName` is the name of the channel. In the above example, the channel name is `Security`.

Depending on collection method, the channel name can be used for the following configuration parameters:
- `log_file`
- `path`
- `channel_path`

<!-- xxx tabs xxx -->
<!-- xxx tab "Events" xxx -->

#### Event collection

To collect Windows Event Logs as Datadog Events, configure channels under the `instances:` section of your `win32_event_log.d/conf.yaml` configuration file.

The agent can be configured to collect Windows Event Logs as Datadog Events in two ways. Each method has its own configuration syntax for channels and for filters (see [Filtering Events](?tab=events#filtering-events)). The legacy method uses WMI and is the default mode for an instance. The newer method uses the Event Log API. We recommend using the Event Log API because it has better performance. To use the Event Log API collection method, set `legacy_mode: false` in each instance.

This example shows entries for the `Security` and `<CHANNEL_2>` channels:

```yaml
init_config:
instances:
  - # WMI - Legacy mode (default)
    legacy_mode: true
    log_file: Security

  - # Event Log API (better performance)
    path: Security
    legacy_mode: false
    filters: {}

  - path: "<CHANNEL_2>" 
    legacy_mode: false
    filters: {}
```

<!-- xxz tab xxx -->
<!-- xxx tab "Logs" xxx -->

#### Log collection

_Available for Agent versions >6.0_

Log collection is disabled by default in the Datadog Agent. To collect Windows Event Logs as Datadog Logs, [activate log collection][18] by setting `logs_enabled: true` in your `datadog.yaml` file.

To collect Windows Event Logs as Datadog Logs, configure channels under the `logs:` section of your `win32_event_log.d/conf.yaml` configuration file. This example shows entries for the `Security` and `<CHANNEL_2>` channels:

```yaml
logs:
  - type: windows_event
    channel_path: Security
    source: windows.events
    service: Windows

  - type: windows_event
    channel_path: "<CHANNEL_2>"
    source: windows.events
    service: myservice
```

Set the corresponding `source` parameter to `windows.events` to benefit from the [integration automatic processing pipeline][5].

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

Edit the `<CHANNEL_2>` parameters with the Windows channel name you want to collect events from.

Finally, [restart the Agent][4].

**Note**: For the Security logs channel, add your Datadog Agent user to the `Event Log Readers` user group.

### Filtering events

Configure one or more filters for the event log. A filter allows you to choose what log events you want to get into Datadog.

  <!-- xxx tabs xxx -->
  <!-- xxx tab "Events" xxx -->

  Use the Windows Event Viewer GUI to list all the event logs available for capture with this integration.

  To determine the exact values, set your filters to use the following PowerShell command:

  ```text
  Get-WmiObject -Class Win32_NTLogEvent
  ```

  For example, to see the latest event logged in the `Security` log file, use:

  ```text
  Get-WmiObject -Class Win32_NTLogEvent -Filter "LogFile='Security'" | select -First 1
  ```

  The values listed in the output of the command can be set in `win32_event_log.d/conf.yaml` to capture the same kind of events.

  <div class="alert alert-info">
  The information given by the  <code>Get-EventLog</code> PowerShell command or the Windows Event ViewerGUI may slightly differ from <code>Get-WmiObject</code>.<br>
  Double-check your filters' values with <code>Get-WmiObject</code> if the integration doesn't capture the events you set up.
  </div>

  Example legacy mode filters:

  - `log_file`: `Application`, `System`, `Setup`, `Security`
  - `type`: `Critical`, `Error`, `Warning`, `Information`, `Audit Success`, `Audit Failure`
  - `source_name`: Any available source name
  - `event_id`: Windows EventLog ID

  Example non-legacy mode filters:

  - `path`: `Application`, `System`, `Setup`, `Security`
  - `type`: `Critical`, `Error`, `Warning`, `Information`, `Success Audit`, `Failure Audit`
  - `source`: Any available source name
  - `id`: event_id: Windows EventLog ID

  See the [sample win32_event_log.d/conf.yaml][3] for all available filter options for respective modes.

  Some example filters:

  ```yaml
  instances:
    # LEGACY MODE
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

  ```yaml
  instances:
    # NON-LEGACY MODE
    - legacy_mode: false
      path: System
      filters:
        source:
        - Microsoft-Windows-Ntfs
        - Service Control Manager
        type:
        - Error
        - Warning
        - Information
        - Success Audit
        - Failure Audit
        id:
        - 7036
  ```

<!-- xxz tab xxx -->
<!-- xxx tab "Logs" xxx -->

  For each filter, add a log processing rule in the configuration file at `win32_event_log.d/conf.yaml`.

  Some example filters:

  ```yaml
    - type: windows_event
      channel_path: Security
      source: windows.events
      service: Windows       
      log_processing_rules:
      - type: include_at_match
        name: relevant_security_events
        pattern: '"EventID":"(1102|4624|4625|4634|4648|4728|4732|4735|4737|4740|4755|4756)"'

    - type: windows_event
      channel_path: Security
      source: windows.events
      service: Windows       
      log_processing_rules:
      - type: exclude_at_match
        name: relevant_security_events
        pattern: '"EventID":"(1102|4624)"'

    - type: windows_event
      channel_path: System
      source: windows.events
      service: Windows       
      log_processing_rules:
      - type: include_at_match
        name: system_errors_and_warnings
        pattern: '"level":"((?i)warning|error)"'

    - type: windows_event
      channel_path: Application
      source: windows.events
      service: Windows       
      log_processing_rules:
      - type: include_at_match
        name: application_errors_and_warnings
        pattern: '"level":"((?i)warning|error)"'
  ```

  Here is an example regex pattern to only collect Windows Events Logs from a certain EventID:

  ```yaml
  logs:
    - type: windows_event
      channel_path: Security
      source: windows.event
      service: Windows
      log_processing_rules:
        - type: include_at_match
          name: include_x01
          pattern: '"EventID":"(101|201|301)"'
  ```

  **Note**: The pattern may vary based on the format of the logs. The [Agent `stream-logs` subcommand][15] can be used to view this format.

  For more examples of filtering logs, see the [Advanced Log Collection documentation][12].

  #### Legacy events
  _Applies to Agent versions less than 7.41_

  Legacy Provider EventIDs have a `Qualifiers` attribute that changes the format of the log, as seen in the [Windows Event Schema][14]. These events have the following XML format, visible in Windows Event Viewer:
  ```xml
  <EventID Qualifiers="16384">3</EventID>
  ```

  The following regex must be used to match these EventIDs:
  ```yaml
  logs:
    - type: windows_event
      channel_path: Security
      source: windows.event
      service: Windows
      log_processing_rules:
        - type: include_at_match
          name: include_legacy_x01
          pattern: '"EventID":{"value":"(101|201|301)"'
  ```

  Agent versions 7.41 and later normalize the EventID field and this legacy pattern is no longer applicable.

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

When you're done setting up filters, [restart the Agent][4] using the Agent Manager (or restart the service).

### Validation

<!-- xxx tabs xxx -->
<!-- xxx tab "Events" xxx -->

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

<!-- xxz tab xxx -->
<!-- xxx tab "Logs" xxx -->

Check the info page in the Datadog Agent Manager or run the [Agent's `status` subcommand][6] and look for `win32_event_log` under the Logs Agent section. It should display a section similar to the following:

```shell
Logs Agent
==========

  [...]

  win32_event_log
  ---------------
    - Type: windows_event
      ChannelPath: System
      Status: OK
```

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

## Data Collected

### Metrics

The Win32 Event log check does not include any metrics.

### Events

All Windows events are forwarded to Datadog.

### Service Checks

The Win32 Event log check does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][7].

## Further Reading

### Documentation

- (Legacy) [Add event log files to the `Win32_NTLogEvent` WMI class][8]

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
[8]: https://docs.datadoghq.com/integrations/guide/add-event-log-files-to-the-win32-ntlogevent-wmi-class/
[9]: https://www.datadoghq.com/blog/monitoring-windows-server-2012
[10]: https://www.datadoghq.com/blog/collect-windows-server-2012-metrics
[11]: https://www.datadoghq.com/blog/windows-server-monitoring
[12]: https://docs.datadoghq.com/agent/logs/advanced_log_collection/?tab=configurationfile
[13]: https://docs.microsoft.com/en-us/windows/win32/eventlog/event-logging
[14]: https://learn.microsoft.com/en-us/windows/win32/wes/eventschema-systempropertiestype-complextype
[15]: https://docs.datadoghq.com/agent/guide/agent-commands/
[16]: https://docs.datadoghq.com/events/
[17]: https://docs.datadoghq.com/logs/
[18]: https://docs.datadoghq.com/agent/logs/#activate-log-collection