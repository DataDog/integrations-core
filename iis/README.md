# IIS Integration

## Overview

Collect IIS metrics aggregated across all of your sites, or on a per-site basis. The IIS Agent check collects metrics for active connections, bytes sent and received, request count by HTTP method, and more. It also sends a service check for each site, letting you know whether it's up or down.

## Setup
### Installation

The IIS check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your IIS servers.

Also, your IIS servers must have the `Win32_PerfFormattedData_W3SVC_WebService` WMI class installed. 

### Configuration
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

#### Connect the Agent

Create a file `iis.yaml` in the Agent's `conf.d` directory:

```
init_config:

instances:
  - host: . # "." means the current host
  # sites:  # to monitor specific sites, or to collect metrics on a per-site basis
  #   - example.com
  #   - dev.example.com
```

To collect metrics on a per-site basis, you *must* use the `sites` option. The Agent collects metrics for each site you list and tags them with the site name — `iis.net.num_connections` tagged with `site:example.com`, and `iis.net.num_connections` tagged with `site:dev.example.com`.

If you don't configure `sites`, the Agent collects all the same metrics, but their values reflect totals across all sites — `iis.net.num_connections` is the total number of connections on the IIS server; you will not have visibility into per-site metrics.

You can also monitor sites on remote IIS servers. See the [sample iis.conf](https://github.com/DataDog/integrations-core/blob/master/iis/conf.yaml.example) for relevant configuration options. By default, this check runs against a single instance - the current machine that the Agent is running on. It will check the WMI performance counters for IIS on that machine.

If you want to check other remote machines as well, you can add one instance per host.
Note: If you also want to check the counters on the current machine, you will haveto create an instance with empty params.

The optional `provider` parameter allows to specify a WMI provider (default to `32` on Datadog Agent 32-bit or `64`). It is used to request WMI data from the non-default provider. Available options are: `32` or `64`. For more information, [review this MSDN article](https://msdn.microsoft.com/en-us/library/aa393067.aspx).

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

[Restart the Agent](https://help.datadoghq.com/hc/en-us/articles/203764515-Start-Stop-Restart-the-Datadog-Agent) to begin sending IIS metrics to Datadog.

### Validation

Run the Agent's `info` subcommand and look for `iis` under the Checks section:

```
  Checks
  ======
    [...]

    iis
    -------
      - instance #0 [OK]
      - Collected 26 metrics, 0 events & 1 service check

    [...]
```

## Data Collected
### Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/iis/metadata.csv) for a list of metrics provided by this integration.

### Events
The IIS check does not include any event at this time.

### Service Checks

`iis.site_up`:

The Agent submits this service check for each configured site in `iis.yaml`. It returns `Critical` if the site's uptime is zero, otherwise `OK`.

## Troubleshooting
Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading
Learn more about infrastructure monitoring and all our integrations on [our blog](https://www.datadoghq.com/blog/)
