# Wmi_check Integration

![WMI metric][12]

## Overview

Get metrics from your Windows applications/servers with Windows Management Instrumentation (WMI) in real time to

* Visualize their performance.
* Correlate their activity with the rest of your applications.

## Setup
### Installation

If you are only collecting standard metrics from Microsoft Windows and other packaged applications, there are no installation steps. If you need to define new metrics to collect from your application, then you have a few options:

1.  Submit perfomance counters using System.Diagnostics in .NET, then access them via WMI.
2.  Implement a COM-based WMI provider for your application. You would typically only do this if you are using a non-.NET language.

To learn more about using System.Diagnostics, refer to [the MSDN documentation here][1]. After adding your metric you should be able to find it in WMI. To browse the WMI namespaces you may find this tool useful: [WMI Explorer][2]. You can find the same information with Powershell [here][3]. Also review the information in the [Datadog Knowledge Base article][4].

If you assign the new metric a category of My_New_Metric, the WMI path will be
`\\<ComputerName>\ROOT\CIMV2:Win32_PerfFormattedData_My_New_Metric`

If the metric isn't showing up in WMI, try running `winmgmt /resyncperf` to force the computer to reregister the performance libraries with WMI.


## Configuration

1.  Click the **Install Integration** button on the WMI Integration Tile.
2.  Open the Datadog Agent Manager on the Windows server.
3.  Edit the `Wmi Check` configuration.

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

<div class="alert alert-info">
The default configuration uses the filter clause to limit the metrics pulled. Either set the filters to valid values or remove them as shown above to collect the metrics.
</div>

The metrics definitions include three components:

* Class property in WMI
* Metric name as it appears in Datadog
* The metric type.

#### Configuration Options
*This feature is available starting with version 5.3 of the agent*

Each WMI query has 2 required options, `class` and `metrics` and six optional options, `host`, `namespace`, `filters`, `provider`, `tag_by`, `constant_tags` and `tag_queries`.

`class` is the name of the WMI class, for example `Win32_OperatingSystem` or `Win32_PerfFormattedData_PerfProc_Process`. You can find many of the standard class names on the [MSDN docs][5]. The `Win32_FormattedData_*` classes provide many useful performance counters by default.

`metrics` is a list of metrics you want to capture, with each item in the
list being a set of \[WMI property name, metric name, metric type].

- The property name is something like `NumberOfUsers` or `ThreadCount`.
  The standard properties are also available on the MSDN docs for each
  class.

- The metric name is the name you want to show up in Datadog.

- The metric type is from the standard choices for all agent checks, such as gauge, rate, histogram or counter.

`host` is the optional target of the WMI query, `localhost` is assumed by default. If you set this option, make sure that Remote Management is enabled on the target host [see here][6] for more information.

`namespace` is the optionnal WMI namespace to connect to (default to `cimv2`).

`filters` is a list of filters on the WMI query you may want. For example, for a process-based WMI class you may want metrics for only certain processes running on your machine, so you could add a filter for each process name. You can also use the '%' character as a wildcard.

`provider` is the optional WMI provider (default to `32` on Datadog Agent 32-bit or `64`). It is used to request WMI data from the non-default provider. Available options are: `32` or `64`.
See [MSDN][7] for more information.

`tag_by` optionally lets you tag each metric with a property from the WMI class you're using. This is only useful when you will have multiple values for your WMI query. The examples below show how you can tag your process metrics with the process name (giving a tag of "name:app_name").

`constant_tags` optionally lets you tag each metric with a set of fixed values.

`tag_queries` optionally lets you specify a list of queries, to tag metrics with a target class property. Each item in the list is a set of `[link source property, target class, link target class property, target property]` where:

- `link source property` contains the link value

- `target class` is the class to link to

- `link target class property` is the target class property to link to

- `target property` contains the value to tag with

It translates to a WMI query:

    SELECT 'target property' FROM 'target class' WHERE 'link target class property' = 'link source property'

<div class="alert alert-info">
Setting this will cause any instance number to be removed from tag_by values i.e. name:process#1 => name:process
</div>

### Validation

[Run the Agent's `status` subcommand][8] and look for `wmi_check` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv][9] for a list of metrics provided by this integration.

### Events
The WMI check does not include any events at this time.

### Service Checks
The WMI check does not include any service checks at this time.

## Troubleshooting
Need help? Contact [Datadog Support][10].

[1]: https://msdn.microsoft.com/en-us/library/system.diagnostics.performancecounter(v=vs.110.aspx)
[2]: https://wmie.codeplex.com/
[3]: https://msdn.microsoft.com/en-us/powershell/scripting/getting-started/cookbooks/getting-wmi-objects--get-wmiobject-
[4]: https://docs.datadoghq.com/integrations/faq/how-to-retrieve-wmi-metrics/
[5]: https://msdn.microsoft.com/en-us/library/windows/desktop/aa394084.aspx
[6]: https://technet.microsoft.com/en-us/library/Hh921475.aspx
[7]: https://msdn.microsoft.com/en-us/library/aa393067.aspx
[8]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[9]: https://github.com/DataDog/integrations-core/blob/master/wmi_check/metadata.csv
[10]: https://docs.datadoghq.com/help/
[12]: https://raw.githubusercontent.com/DataDog/integrations-core/master/wmi_check/images/wmimetric.png
