# Agent Check: Windows Event Log

## Overview

This integration watches for Windows Event Logs and forwards them to Datadog. 

Enable this integration to:

- Track system and application events in Datadog.
- Correlate system and application events with the rest of your application.

For more information, see the [Windows Event Logging documentation][13].

## Setup

### Installation

The Windows Event Log check is included in the [Datadog Agent][1] package. There is no additional installation required.

### Configuration

Windows Event Logs can be collected as one or both of the following methods.

- As [Datadog Events][16]
- As [Datadog Logs][17]

Both methods are configured in `win32_event_log.d/conf.yaml` in the `conf.d/` folder at the root of your [Agent's configuration directory][2]. See the [sample win32_event_log.d/conf.yaml][3] for all available configuration options.


#### List Windows Event channels

First, identify the Windows Event Log channels you want to monitor. 

Depending on collection method, the channel name can be used for the following configuration parameters:

- Datadog Logs: `channel_path`
- Datadog Events: `path`
- Datadog Events (legacy): `log_file`

##### PowerShell

To see a list of channels, run the following command in PowerShell:

```powershell
Get-WinEvent -ListLog *
```

To see the most active channels, run the following command in PowerShell:

```powershell
Get-WinEvent -ListLog * | sort RecordCount -Descending
```

This command displays channels in the format `LogMode MaximumSizeInBytes RecordCount LogName`. 

Example response:

```text
LogMode  MaximumSizeInBytes RecordCount LogName 
Circular          134217728      249896 Security
Circular            5242880        2932 <CHANNEL_2>
```

The value under the column `LogName` is the name of the channel. In the example above, the channel name is `Security`.

##### Windows Event Viewer

To find the channel name for an Event Log in the Windows Event Viewer, open the Event Log Properties window and refer to the `Full Name` field. In the following example, the channel name is `Microsoft-Windows-Windows Defender/Operational`.

![Windows Event Log][19]

<!-- xxx tabs xxx -->

<!-- xxx tab "Logs" xxx -->

#### Log collection

_Available for Agent versions 6.0 or later_

Log collection is disabled by default in the Datadog Agent. To collect Windows Event Logs as Datadog logs, [activate log collection][18] by setting `logs_enabled: true` in your `datadog.yaml` file.

To collect Windows Event Logs as Datadog logs, configure channels under the `logs:` section of your `win32_event_log.d/conf.yaml` configuration file. This example shows entries for the `Security` and `<CHANNEL_2>` channels:

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
<!-- xxx tab "Events" xxx -->

#### Event collection using the Event Log API (Recommended)

The Datadog Agent can be configured to collect Windows Event Logs as Datadog events using the Event Log API. Datadog recommends using the Event Log API because it has better performance than the legacy method below. Note, each method has its own configuration syntax for channels and for filters. For more information, see [Filtering Events](?tab=events#filtering-events). 

To collect Windows Event Logs as Datadog events, configure channels under the `instances:` section of your `win32_event_log.d/conf.yaml` configuration file. 

  </br> Set `legacy_mode: false` in each instance. If `legacy_mode: false` is set, the `path` is required to be set in the `\win32_event_log.d\conf.yaml` file. 

  </br> This example shows entries for the `Security` and `<CHANNEL_2>` channels:

  ```yaml
  init_config:
  instances:
    - # Event Log API 
      path: Security
      legacy_mode: false
      filters: {}

    - path: "<CHANNEL_2>" 
      legacy_mode: false
      filters: {}
  ```

Agent versions 7.49 and later support setting `legacy_mode` in the shared `init_config` section. This sets the default for all instances and no longer requires you to set `legacy_mode` individually for each instance. However, the option can still be set on a per-instance basis.

  ```yaml
  init_config:
      legacy_mode: false
  instances:
    - # Event Log API
      path: Security
      filters: {}

    - path: "<CHANNEL_2>"
      filters: {}
  ```

#### Event collection using Legacy Mode (Deprecated)

The legacy method uses WMI (Windows Management Instrumentation) and was deprecated in Agent version 7.20. 

To collect Windows Event Logs as Datadog events, configure channels under the `instances:` section of your `win32_event_log.d/conf.yaml` configuration file.
  
  </br> To use Legacy Mode, set `legacy_mode` to `true`. Then, set at least one of the following filters: `source_name`, `event_id`, `message_filters`, `log_file`, or `type`.

  </br> This example shows entries for the `Security` and `<CHANNEL_2>` channels:

  ```yaml
  init_config:
  instances:
    - # WMI (default)
      legacy_mode: true
      log_file:
        - Security
        
    - legacy_mode: true
      log_file:
        - "<CHANNEL_2>"
  ```
  
  For more information, see [Add event log files to the `Win32_NTLogEvent` WMI class][28].

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

Edit the `<CHANNEL_2>` parameters with the Windows channel name you want to collect events from.

Finally, [restart the Agent][4].

**Note**: For the Security logs channel, add your Datadog Agent user to the `Event Log Readers` user group.

### Filtering events

Configure one or more filters for the event log. A filter allows you to choose what log events you want to get into Datadog.

<!-- xxx tabs xxx -->

<!-- xxx tab "Logs" xxx -->

You can use the `query`, as well as the `log_processing_rules` regex option, to filter event logs. Datadog recommends using the `query` option which is faster at high rates of Windows Event Log generation and requires less CPU and memory than the `log_processing_rules` filters. When using the `log_processing_rules` filters, the Agent is forced to process and format each event, even if it will be excluded by `log_processing_rules` regex. With the `query` option, these events are not reported to the Agent.

You can use the `query` option to filter events with an [XPATH or structured XML query][21]. The `query` option can reduce the number of events that are processed by `log_processing_rules` and improve performance. There is an expression limit on the syntax of XPath and XML queries. For additional filtering, use `log_processing_rules` filters.

Datadog recommends creating and testing the query in Event Viewer's filter editor until the events shown in Event Viewer match what you want the Agent to collect.

![Filter Current Log][23]

Then, copy and paste the query into the Agent configuration. 

```yaml
  # collect Critical, Warning, and Error events
  - type: windows_event
    channel_path: Application
    source: windows.events
    service: Windows       
    query: '*[System[(Level=1 or Level=2 or Level=3)]]'
      
  - type: windows_event
    channel_path: Application
    source: windows.events
    service: Windows       
    query: |
      <QueryList>
        <Query Id="0" Path="Application">
          <Select Path="Application">*[System[(Level=1 or Level=2 or Level=3)]]</Select>
        </Query>
      </QueryList>
```

![XML Query][24]

In addition to the `query` option, events can be further filtered with log processing rules.

Some example filters include the following:

```yaml
  - type: windows_event
    channel_path: Security
    source: windows.events
    service: Windows       
    log_processing_rules:
    - type: include_at_match
      name: relevant_security_events
      pattern: '"EventID":(?:{"value":)?"(1102|4624|4625|4634|4648|4728|4732|4735|4737|4740|4755|4756)"'

  - type: windows_event
    channel_path: Security
    source: windows.events
    service: Windows       
    log_processing_rules:
    - type: exclude_at_match
      name: relevant_security_events
      pattern: '"EventID":(?:{"value":)?"(1102|4624)"'

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
        pattern: '"EventID":(?:{"value":)?"(101|201|301)"'
```

**Note**: The pattern may vary based on the format of the logs. The [Agent `stream-logs` subcommand][15] can be used to view this format.

For more examples of filtering logs, see the [Advanced Log Collection documentation][12].

#### Legacy events
_Applies to Agent versions < 7.41_

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
        pattern: '"EventID":(?:{"value":)?"(101|201|301)"'
```

Agent versions 7.41 or later normalize the EventID field. This removes the need for the substring, `(?:{"value":)?`, from legacy pattern as it is no longer applicable. A shorter regex pattern can be used from versions 7.41 or later as seen below:

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

<!-- xxz tab xxx -->
<!-- xxx tab "Events" xxx -->

Use the Windows Event Viewer GUI to list all the event logs available for capture with this integration.

To determine the exact values, set your filters to use the following PowerShell command:

```text
Get-WmiObject -Class Win32_NTLogEvent
```

For example, to see the latest event logged in the `Security` log file, use the following:

```text
Get-WmiObject -Class Win32_NTLogEvent -Filter "LogFile='Security'" | select -First 1
```

The values listed in the output of the command can be set in `win32_event_log.d/conf.yaml` to capture the same kind of events.

<div class="alert alert-info">
The information given by the  <code>Get-EventLog</code> PowerShell command or the Windows Event ViewerGUI may slightly differ from <code>Get-WmiObject</code>.<br> Double check your filters' values with <code>Get-WmiObject</code> if the integration does not capture the events you set up.
</div>

#### Filtering events using the Event Log API (Recommended)

The configuration option using the Event Log API includes the following filters:

  - `path`: `Application`, `System`, `Setup`, `Security`
  - `type`: `Critical`, `Error`, `Warning`, `Information`, `Success Audit`, `Failure Audit`
  - `source`: Any available source name
  - `id`: event_id: Windows EventLog ID

  See the [sample win32_event_log.d/conf.yaml][3] for all available filter options. 

  This example filter uses Event Log API method.

  ```yaml
  instances:
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

You can use the [`query` option][20] to filter events with an [XPATH or structured XML query][21]. Datadog recommends creating the query in Event Viewer's filter editor until the events shown in Event Viewer match what you want the Datadog Agent to collect. The `filters` option is ignored when the `query` option is used.

  ```yaml
  init_config:
  instances:
    # collect Critical, Warning, and Error events
    - path: Application
      legacy_mode: false
      query: '*[System[(Level=1 or Level=2 or Level=3)]]'
      
    - path: Application
      legacy_mode: false
      query: |
        <QueryList>
          <Query Id="0" Path="Application">
            <Select Path="Application">*[System[(Level=1 or Level=2 or Level=3)]]</Select>
          </Query>
        </QueryList>
 ```

#### Filtering events using Legacy Mode (Deprecated)

The configuration option using the Legacy Mode includes the following filters:

  - `log_file`: `Application`, `System`, `Setup`, `Security`
  - `type`: `Critical`, `Error`, `Warning`, `Information`, `Audit Success`, `Audit Failure`
  - `source_name`: Any available source name
  - `event_id`: Windows EventLog ID

  This example filter uses the Legacy Mode method.

  ```yaml
  instances:
    # Legacy
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
The legacy method does not support the `query` option. Only the Event Log API method (setting `legacy_mode: false`) and the Logs Tailer supports the `query` option.

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

When you're done setting up filters, [restart the Agent][4] using the Agent Manager, or restart the service.

### Validation

<!-- xxx tabs xxx -->
<!-- xxx tab "Logs" xxx -->

Check the information page in the Datadog Agent Manager or run the [Agent's `status` subcommand][6] and look for `win32_event_log` under the Logs Agent section. 

It should display a section similar to the following:

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
<!-- xxx tab "Events" xxx -->

Check the information page in the Datadog Agent Manager or run the [Agent's `status` subcommand][6] and look for `win32_event_log` under the Checks section. 

It should display a section similar to the following:

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
<!-- xxz tabs xxx -->

## Data Collected

### Metrics

The Windows Event Log check does not include any metrics.

### Events

All Windows events are forwarded to Datadog.

### Service Checks

The Windows Event Log check does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][7] with an [Agent Flare][25].

### Log processing rules are not working

If you are using log processing rules to filter out logs, verify that the raw logs match the regular expression (regex) pattern you configured. In the configuration below, log levels must be either `warning` or `error`. Any other value is excluded.

```yaml
    - type: windows_event
      channel_path: System
      source: windows.events
      service: Windows       
      log_processing_rules:
      - type: include_at_match
        name: system_errors_and_warnings
        pattern: '"level":"((?i)warning|error)"'
```

To troubleshoot your log processing rules:
1. Remove or comment out the `log_processing_rules` stanza.
2. Restart the Agent.
3. Send a test log that includes the values you're attempting to catch. If the log appears in Datadog, there is probably an issue with your regex. Compare your regex against the log file to make sure you're capturing the right phrases.

## Further Reading

Additional helpful documentation, links, and articles:

- [Advanced Log Collection][26]
- [Monitoring Windows Server 2012][9]
- [How to collect Windows Server 2012 metrics][10]
- [Monitoring Windows Server 2012 with Datadog][11]
- [Monitor Windows event logs with Datadog][27]

[1]: https://app.datadoghq.com/account/settings/agent/latest?platform=windows
[2]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[3]: https://github.com/DataDog/integrations-core/blob/master/win32_event_log/datadog_checks/win32_event_log/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/logs/processing/pipelines/#integration-pipelines
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://docs.datadoghq.com/help/
[9]: https://www.datadoghq.com/blog/monitoring-windows-server-2012
[10]: https://www.datadoghq.com/blog/collect-windows-server-2012-metrics
[11]: https://www.datadoghq.com/blog/windows-server-monitoring
[12]: https://docs.datadoghq.com/agent/logs/advanced_log_collection/?tab=configurationfile#filter-logs
[13]: https://docs.microsoft.com/en-us/windows/win32/eventlog/event-logging
[14]: https://learn.microsoft.com/en-us/windows/win32/wes/eventschema-systempropertiestype-complextype
[15]: https://docs.datadoghq.com/agent/guide/agent-commands/
[16]: https://docs.datadoghq.com/service_management/events/
[17]: https://docs.datadoghq.com/logs/
[18]: https://docs.datadoghq.com/agent/logs/#activate-log-collection
[19]: https://raw.githubusercontent.com/DataDog/integrations-core/master/win32_event_log/images/windows-defender-operational-event-log-properties.png
[20]: https://github.com/DataDog/integrations-core/blob/10296a69722b75098ed0b45ce55f0309a1800afd/win32_event_log/datadog_checks/win32_event_log/data/conf.yaml.example#L74-L89
[21]: https://learn.microsoft.com/en-us/windows/win32/wes/consuming-events
[22]: https://github.com/DataDog/integrations-core/blob/master/win32_event_log/datadog_checks/win32_event_log/data/conf.yaml.example#L87C32-L87C32
[23]: https://raw.githubusercontent.com/DataDog/integrations-core/master/win32_event_log/images/filter-event-viewer.png
[24]: https://raw.githubusercontent.com/DataDog/integrations-core/master/win32_event_log/images/xml-query-event-viewer.png
[25]: https://docs.datadoghq.com/agent/troubleshooting/send_a_flare/?tab=agentv6v7
[26]: https://docs.datadoghq.com/agent/logs/advanced_log_collection/?tab=configurationfile
[27]: https://www.datadoghq.com/blog/monitor-windows-event-logs-with-datadog/
[28]: https://docs.datadoghq.com/integrations/guide/add-event-log-files-to-the-win32-ntlogevent-wmi-class/
