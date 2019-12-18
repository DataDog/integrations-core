# IIS Integration

![IIS Graph][1]

## Overview

Collect IIS metrics aggregated across all of your sites, or on a per-site basis. The IIS Agent check collects metrics for active connections, bytes sent and received, request count by HTTP method, and more. It also sends a service check for each site, letting you know whether it's up or down.

## Setup
### Installation

The IIS check is packaged with the Agent. To start gathering your IIS metrics and logs, you need to:

1. [Install the Agent][3] on your IIS servers.

2. Your IIS servers must have the `Win32_PerfFormattedData_W3SVC_WebService` WMI class installed.
  You can check for this using the following command:
  ```
  Get-WmiObject -List -Namespace root\cimv2 | select -Property name | where name -like "*Win32_PerfFormattedData_W3SVC*"
  ```

  This class should be installed as part of the web-http-common Windows Feature:

  ```
  PS C:\Users\vagrant> Get-WindowsFeature web-* | where installstate -eq installed | ft -AutoSize

  Display Name                       Name               Install State
  ------------                       ----               -------------
  [X] Web Server (IIS)               Web-Server             Installed
  [X] Web Server                     Web-WebServer          Installed
  [X] Common HTTP Features           Web-Common-Http        Installed
  [X] Default Document               Web-Default-Doc        Installed
  [X] Directory Browsing             Web-Dir-Browsing       Installed
  [X] HTTP Errors                    Web-Http-Errors        Installed
  [X] Static Content                 Web-Static-Content     Installed
  ```

  You can add the missing features with `install-windowsfeature web-common-http`. This requires a restart of the system to work properly.

### Configuration

Edit the `iis.d/conf.yaml` file  in the [Agent's `conf.d` directory][4] at the root of your [Agent's configuration directory][5],

#### Prepare IIS

On your IIS servers, first resync the WMI counters.

On Windows <= 2003 (or equivalent), run the following in cmd.exe:

```
C:/> winmgmt /clearadap
C:/> winmgmt /resyncperf
```

On Windows >= 2008 (or equivalent), instead run:

```
C:/> winmgmt /resyncperf
```

#### Metric Collection

 * Add this configuration block to your `iis.d/conf.yaml` file to start gathering your [IIS metrics](#metrics):

```
init_config:

instances:
  - host: . # "." means the current host
  # sites:  # to monitor specific sites, or to collect metrics on a per-site basis
  #   - example.com
  #   - dev.example.com
```

Use the `sites` option to collect metrics on a per-site basis. When setup, the Agent collects metrics for each site you list and tags them with the corresponding site name. If you don't configure `sites`, the Agent collects the same metrics, but their values reflect totals across all sites.

You can also monitor sites on remote IIS servers. See the [sample iis.d/conf.yaml][6] for relevant configuration options. By default, this check runs against a single instance - the current machine that the Agent is running on. It will check the WMI performance counters for IIS on that machine.

If you want to check other remote machines as well, you can add one instance per host.
Note: If you also want to check the counters on the current machine, you will haveto create an instance with empty params.

The optional `provider` parameter allows to specify a WMI provider (default to `32` on Datadog Agent 32-bit or `64`). It is used to request WMI data from the non-default provider. Available options are: `32` or `64`. For more information, [review this MSDN article][7].

The `sites` parameter allows you to specify a list of sites you want to read metrics from. With sites specified, metrics will be tagged with the site name. If you don't define any sites, the check will pull the aggregate values across all sites.

Here's an example of configuration that would check the current machine and a remote machine called MYREMOTESERVER. For the remote host we are only pulling metrics from the default site.

```
- host: .
  tags:
    - myapp1
  sites:
    - Default Web Site
- host: MYREMOTESERVER
  username: MYREMOTESERVER\fred
  password: mysecretpassword
  is_2008: false
```

* `is_2008` (Optional) - NOTE: because of a typo in IIS6/7 (typically on W2K8) where perfmon reports TotalBytesTransferred as TotalBytesTransfered, you may have to enable this to grab the IIS metrics in that environment.

* See the [sample iis.yaml][6] for all available configuration options.

* [Restart the Agent][8] to begin sending IIS metrics to Datadog.

#### Log collection

**Available for Agent >6.0**

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

    ```yaml
      logs_enabled: true
    ```

2. Add this configuration block to your `iis.d/conf.yaml` file to start collecting your IIS Logs:

    ```yaml
      logs:
          - type: file
            path: C:\inetpub\logs\LogFiles\W3SVC1\u_ex*
            service: myservice
            source: iis
            sourcecategory: http_web_access
    ```

    Change the `path` and `service` parameter values and configure them for your environment.
    See the [sample iis.d/conf.yaml][6] for all available configuration options.

3. [Restart the Agent][8].

### Validation

[Run the Agent's status subcommand][10] and look for `iis` under the Checks section.

## Data Collected
### Metrics

See [metadata.csv][11] for a list of metrics provided by this integration.

### Events
The IIS check does not include any events.

### Service Checks

**iis.site_up**:<br>
The Agent submits this service check for each configured site in `iis.yaml`. It returns `Critical` if the site's uptime is zero, otherwise returns `OK`.

## Troubleshooting
Need help? Contact [Datadog support][12].

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/iis/images/iisgraph.png
[3]: https://app.datadoghq.com/account/settings#agent
[4]: https://docs.datadoghq.com/agent/basic_agent_usage/windows/#agent-check-directory-structure
[5]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[6]: https://github.com/DataDog/integrations-core/blob/master/iis/datadog_checks/iis/data/conf.yaml.example
[7]: https://msdn.microsoft.com/en-us/library/aa393067.aspx
[8]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[10]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[11]: https://github.com/DataDog/integrations-core/blob/master/iis/metadata.csv
[12]: https://docs.datadoghq.com/help
