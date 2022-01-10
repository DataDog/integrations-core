# Wmi_check Integration

![WMI metric][1]

## Overview

Get metrics from your Windows applications and servers with Windows Management Instrumentation (WMI) in real time to

- Visualize their performance.
- Correlate their activity with the rest of your applications.

**Note:** It is recommended that the [PDH check][2] be used instead in all cases due to its significantly lower overhead and thus better scalability.

## Setup

### Installation

If you are only collecting standard metrics from Microsoft Windows and other packaged applications, there are no installation steps. If you need to define new metrics to collect from your application, then you have a few options:

1. Submit performance counters using System.Diagnostics in .NET, then access them via WMI.
2. Implement a COM-based WMI provider for your application. You would typically only do this if you are using a non-.NET language.

To learn more about using System.Diagnostics, see [the MSDN documentation][3]). After adding your metric you should be able to find it in WMI. To browse the WMI namespaces you may find this tool useful: [WMI Explorer][4]. You can find the same information with Powershell [here][5]. Also review the information in the [Datadog Knowledge Base article][6].

If you assign the new metric a category of My_New_Metric, the WMI path is
`\\<ComputerName>\ROOT\CIMV2:Win32_PerfFormattedData_My_New_Metric`

If the metric isn't showing up in WMI, try running `winmgmt /resyncperf` to force the computer to reregister the performance libraries with WMI.

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

_This feature is available starting with version 5.3 of the agent_

Each WMI query has 2 required options, `class` and `metrics` and six optional options, `host`, `namespace`, `filters`, `provider`, `tag_by`, `constant_tags` and `tag_queries`.

- `class` is the name of the WMI class, for example `Win32_OperatingSystem` or `Win32_PerfFormattedData_PerfProc_Process`. You can find many of the standard class names on the [MSDN docs][7]. The `Win32_FormattedData_*` classes provide many useful performance counters by default.

- `metrics` is a list of metrics you want to capture, with each item in the
  list being a set of `[<WMI_PROPERTY_NAME>, <METRIC_NAME>, <METRIC_TYPE>]`:

  - `<WMI_PROPERTY_NAME>` is something like `NumberOfUsers` or `ThreadCount`. The standard properties are also available on the MSDN docs for each class.
  - `<METRIC_NAME>` is the name you want to show up in Datadog.
  - `<METRIC_TYPE>` is from the standard choices for all agent checks, such as gauge, rate, histogram or counter.

- `host` is the optional target of the WMI query, `localhost` is assumed by default. If you set this option, make sure that Remote Management is enabled on the target host [see here][8] for more information.

- `namespace` is the optional WMI namespace to connect to (default to `cimv2`).

- `filters` is a list of filters on the WMI query you may want. For example, for a process-based WMI class you may want metrics for only certain processes running on your machine, so you could add a filter for each process name. You can also use the '%' character as a wildcard.

- `provider` is the optional WMI provider (default to `32` on Datadog Agent 32-bit or `64`). It is used to request WMI data from the non-default provider. Available options are: `32` or `64`.
  See [MSDN][9] for more information.

- `tag_by` optionally lets you tag each metric with a property from the WMI class you're using. This is only useful when you have multiple values for your WMI query.

- `tags` optionally lets you tag each metric with a set of fixed values.

- `tag_queries` optionally lets you specify a list of queries, to tag metrics with a target class property. Each item in the list is a set of `[<LINK_SOURCE_PROPERTY>, <TARGET_CLASS>, <LINK_TARGET_CLASS_PROPERTY>, <TARGET_PROPERTY>]` where:

  - `<LINK_SOURCE_PROPERTY>` contains the link value
  - `<TARGET_CLASS>` is the class to link to
  - `<LINK_TARGET_CLASS_PROPERTY>` is the target class property to link to
  - `<TARGET_PROPERTY>` contains the value to tag with

  It translates to a WMI query:
  `SELECT '<TARGET_PROPERTY>' FROM '<TARGET_CLASS>' WHERE '<LINK_TARGET_CLASS_PROPERTY>' = '<LINK_SOURCE_PROPERTY>'`

##### Example

The setting `[IDProcess, Win32_Process, Handle, CommandLine]` tags each process with its command line. Any instance number will be removed from tag_by values i.e. name:process#1 => name:process. NB: The agent must be running under an **Administrator** account for this to work as the `CommandLine` property is not accessible to non-admins.

### Validation

[Run the Agent's `status` subcommand][10] and look for `wmi_check` under the Checks section.

## Data Collected

### Metrics

All metrics collected by the WMI check are forwarded to Datadog as [custom metrics][11], which may impact your [billing][12].

### Events

The WMI check does not include any events.

### Service Checks

The WMI check does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][13].

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/wmi_check/images/wmimetric.png
[2]: https://docs.datadoghq.com/integrations/pdh_check/
[3]: https://msdn.microsoft.com/en-us/library/system.diagnostics.performancecounter(v=vs.110.aspx
[4]: https://wmie.codeplex.com
[5]: https://msdn.microsoft.com/en-us/powershell/scripting/getting-started/cookbooks/getting-wmi-objects--get-wmiobject-
[6]: https://docs.datadoghq.com/integrations/faq/how-to-retrieve-wmi-metrics/
[7]: https://msdn.microsoft.com/en-us/library/windows/desktop/aa394084.aspx
[8]: https://technet.microsoft.com/en-us/library/Hh921475.aspx
[9]: https://msdn.microsoft.com/en-us/library/aa393067.aspx
[10]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[11]: https://docs.datadoghq.com/developers/metrics/custom_metrics/
[12]: https://docs.datadoghq.com/account_management/billing/custom_metrics/
[13]: https://docs.datadoghq.com/help/
