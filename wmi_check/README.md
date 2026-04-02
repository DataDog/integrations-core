# Wmi_check Integration

![WMI metric][1]

## Overview

**Note 1:** Although the WMI check can still be used to collect Windows Performance Counters (and was previously the only method available), it is now recommended to use the dedicated [Windows Performance Counters integration][2]. This integration leverages the native Performance Counters API, making it more efficient and easier to configure. In practice, you should avoid using the `Win32_PerfFormattedData_XYZ` WMI class, as it merely acts as an alias for a Performance Counter Object/Counterset.

**Note 2:** Certain WMI classes, such as `Win32_Product` or `Win32_UserAccount`, are not well-suited for frequent queries, as they can be slow to respond or may cause high CPU usage. Before using any WMI class to collect telemetry, carefully test its performance to ensure it is appropriate for use in a production environment.

The built-in Windows WMI ecosystem offers rich, and in many cases exclusive, access to Windows and Microsoft features and products telemetry. This WMI Check allows mapping rows and columns from WMI class datasets to Datadog metrics and their tags, making it easier to extract meaningful telemetry. Additionally, it supports joining two WMI class datasets, allowing for correlations between datasets that would otherwise be impossible to achieve.

**Minimum Agent version:** 6.0.0

## Setup

### [Default] Agent User Privilege

[The default user][15] configured during the standard Agent installation is sufficient to collect telemetry from many WMI classes. However, some WMI classes may require a user with elevated privileges to access their data.

### Configuration

1. Click the **Install Integration** button on the WMI Integration Tile.
2. Open the Datadog Agent Manager on the Windows server.
3. Edit the `Wmi Check` configuration.

```yaml
init_config:
instances:
  - class: Win32_OperatingSystem
    metrics:
      - [NumberOfProcesses, system.proc.count, gauge]
      - [NumberOfUsers, system.users.count, gauge]
  - class: Win32_PerfFormattedData_PerfProc_Process
    metrics:
      - [ThreadCount, proc.threads.count, gauge]
      - [VirtualBytes, proc.mem.virtual, gauge]
      - [PercentProcessorTime, proc.cpu_pct, gauge]
    tag_by: Name
  - class: Win32_PerfFormattedData_PerfProc_Process
    metrics:
      - [IOReadBytesPerSec, proc.io.bytes_read, gauge]
    tag_by: Name
    tag_queries:
      - [IDProcess, Win32_Process, Handle, CommandLine]
```

<div class="alert alert-info">
The default configuration uses the filter clause to limit the metrics pulled. Either set the filters to valid values or remove them as shown above to collect the metrics.
</div>

The metrics definitions include three components:

- Class property in WMI.
- Metric name as it appears in Datadog.
- The metric type.

The following sample configuration populates many more metrics on a Windows 2012 server.
```yaml
init_config:

instances:
  # Fetch the number of processes and users.
  - class: Win32_OperatingSystem
    metrics:
      - [NumberOfProcesses, system.proc.count, gauge]
      - [NumberOfUsers, system.users.count, gauge]

# Paging info
  - class: Win32_PerfFormattedData_PerfOS_Memory
    metrics:
      - [PageFaultsPersec, system.mem.page.faults, gauge]
      - [PageReadsPersec, system.mem.page.reads, gauge]
      - [PagesInputPersec, system.mem.page.input, gauge]
      - [AvailableMBytes, system.mem.avail, gauge]
      - [CommitLimit, system.mem.limit, gauge]
      # Cache bytes metric for disk info
      - [CacheBytes, system.mem.fs_cache, gauge]

# Paging file
  - class: Win32_PerfFormattedData_PerfOS_PagingFile
    metrics:
      - [PercentUsage, system.mem.page.pct, gauge]
    tag_by: Name
  # Fetch the number of processes
  - class: Win32_PerfFormattedData_PerfOS_System
    metrics:
      - [ProcessorQueueLength, system.proc.queue, gauge]

  - class: Win32_PerfFormattedData_PerfOS_Processor
    metrics:
      - [PercentProcessorTime, system.cpu.pct, gauge]
      - [PercentPrivilegedTime, system.cpu.priv.pct, gauge]
      - [PercentDPCTime, system.cpu.dpc.pct, gauge]
      - [PercentInterruptTime, system.cpu.interrupt.pct, gauge]
      - [DPCsQueuedPersec, system.cpu.dpc.queue, gauge]
    tag_by: Name

# Context switches
  - class: Win32_PerfFormattedData_PerfProc_Thread
    metrics:
      - [ContextSwitchesPersec, system.proc.context_switches, gauge]
    filters:
      - Name: _total/_total

# Disk info
  - class: Win32_PerfFormattedData_PerfDisk_LogicalDisk
    metrics:
      - [PercentFreeSpace, system.disk.free.pct, gauge]
      - [PercentIdleTime, system.disk.idle, gauge]
      - [AvgDisksecPerRead, system.disk.read_sec, gauge]
      - [AvgDisksecPerWrite, system.disk.write_sec, gauge]
      - [DiskWritesPersec, system.disk.writes, gauge]
      - [DiskReadsPersec, system.disk.reads, gauge]
      - [AvgDiskQueueLength, system.disk.queue, gauge]
    tag_by: Name

  - class: Win32_PerfFormattedData_Tcpip_TCPv4
    metrics:
      - [SegmentsRetransmittedPersec, system.net.tcp.retrans_seg, gauge]
    tag_by: Name
```
#### Configuration options

_This feature is available starting with version 5.3 of the Agent_

Each WMI query has 2 required options, `class` and `metrics` and six optional options, `host`, `namespace`, `filters`, `provider`, `tag_by`, and `tag_queries`.

- `class` is the name of the WMI class, for example `Win32_OperatingSystem` or `Win32_PerfFormattedData_PerfProc_Process`. You can find many of the standard class names on the [MSDN docs][7]. The `Win32_FormattedData_*` classes provide many useful performance counters by default.

- `metrics` is a list of metrics you want to capture, with each item in the
  list being a set of `[<WMI_PROPERTY_NAME>, <METRIC_NAME>, <METRIC_TYPE>]`:

  - `<WMI_PROPERTY_NAME>` is something like `NumberOfUsers` or `ThreadCount`. The standard properties are also available on the MSDN docs for each class.
  - `<METRIC_NAME>` is the name you want to show up in Datadog.
  - `<METRIC_TYPE>` is from the standard choices for all agent checks, such as gauge, rate, histogram or counter.

- `host` is the optional target of the WMI query, `localhost` is assumed by default. If you set this option, make sure that Remote Management is enabled on the target host. See [Configure Remote Management in Server Manager][8] for more information.

- `namespace` is the optional WMI namespace to connect to (default to `cimv2`).

- `filters` is a list of filters on the WMI query you may want. For example, for a process-based WMI class you may want metrics for only certain processes running on your machine, so you could add a filter for each process name. You can also use the '%' character as a wildcard.

- `provider` is the optional WMI provider (default to `32` on Datadog Agent 32-bit or `64`). It is used to request WMI data from the non-default provider. Available options are: `32` or `64`.
  See [MSDN][9] for more information.

- `tag_by` optionally lets you tag each metric with a property from the WMI class you're using. This is only useful when you have multiple values for your WMI query. For Agent versions 7.74 and later, aliases can be set for property tags by appending `AS <ALIAS_NAME>` to the property name. For example: `Name AS wmi_name` is tagged as `wmi_name:value` instead of `Name:value`.

- `tags` optionally lets you tag each metric with a set of fixed values.

- `tag_queries` optionally lets you specify a list of queries, to tag metrics with a target class property. Each item in the list is a set of `[<LINK_SOURCE_PROPERTY>, <TARGET_CLASS>, <LINK_TARGET_CLASS_PROPERTY>, <TARGET_PROPERTY> AS <TAG_ALIAS>]` where:

  - `<LINK_SOURCE_PROPERTY>` contains the link value
  - `<TARGET_CLASS>` is the class to link to
  - `<LINK_TARGET_CLASS_PROPERTY>` is the target class property to link to
  - `<TARGET_PROPERTY>` contains the value to tag with
  - `<TAG_ALIAS>` is the alias to use for the tag. If not provided, the target property's name is used. This functionality is available with Agent versions 7.74 and later.

  It translates to a WMI query:
  `SELECT '<TARGET_PROPERTY>' FROM '<TARGET_CLASS>' WHERE '<LINK_TARGET_CLASS_PROPERTY>' = '<LINK_SOURCE_PROPERTY>'`

##### Example

The setting `[IDProcess, Win32_Process, Handle, CommandLine]` tags each process with its command line. For example: `commandline:agent.exe`.

An alias can be set for these tags with the setting `[IDProcess, Win32_Process, Handle, CommandLine AS cmd]`. For example: `cmd:agent.exe`.

Any instance number is removed from `tag_by` values, for example: `name:process#1` => `name:process`. **Note**: The Agent must be running under an **Administrator** account for this to work because the `CommandLine` property is not accessible to non-admins.

### Validation

Run the [Agent's status subcommand][10] and look for `wmi_check` under the Checks section.

## Data Collected

### Metrics

All metrics collected by the WMI check are forwarded to Datadog as [custom metrics][11], which may impact your [billing][12].

### Events

The WMI check does not include any events.

### Service Checks

The WMI check does not include any service checks.

## Finding WMI classes

#### List WMI Namespaces

Many WMI classes reside in the default `ROOT\cimv2` namespace, but Windows features and products often define additional namespaces that expose namespace-specific WMI classes. To list all available namespaces on a host, run the following PowerShell command:

```
PS> Get-WmiObject -Namespace Root -Class __Namespace | Select Name
```

#### List WMI Namespace Classes

To list all WMI classes available in `XYZ` namespace, run the following PowerShell command:

```
Get-WmiObject -List -Namespace ROOT\xyz | Select Name
```

... or drop `-Namespace` parameter for the default namespace.

To find a WMI class `abc`, run the following PowerShell command:

```
Get-WmiObject -List | WHERE{$_.Name -Like "*abc*"}
```

#### WMI Provider Documentation

Microsoft provides detailed documentation for many but not all WMI classes in [WMI Providers][13].

## Troubleshooting

Need help? Contact [Datadog support][14].

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/wmi_check/images/wmimetric.png
[2]: https://docs.datadoghq.com/integrations/windows_performance_counters/
[3]: https://docs.microsoft.com/en-us/dotnet/api/system.diagnostics.performancecounter
[4]: https://github.com/vinaypamnani/wmie2/releases
[5]: https://docs.microsoft.com/en-us/powershell/module/microsoft.powershell.management/get-wmiobject
[6]: https://docs.datadoghq.com/integrations/guide/retrieving-wmi-metrics/
[7]: https://msdn.microsoft.com/en-us/library/windows/desktop/aa394084.aspx
[8]: https://technet.microsoft.com/en-us/library/Hh921475.aspx
[9]: https://msdn.microsoft.com/en-us/library/aa393067.aspx
[10]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[11]: https://docs.datadoghq.com/developers/metrics/custom_metrics/
[12]: https://docs.datadoghq.com/account_management/billing/custom_metrics/
[13]: https://learn.microsoft.com/en-us/windows/win32/wmisdk/wmi-providers
[14]: https://docs.datadoghq.com/help/
[15]: https://docs.datadoghq.com/agent/guide/windows-agent-ddagent-user/
