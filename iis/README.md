# IIS Integration

# Overview

Collect IIS metrics aggregated across all of your sites, or on a per-site basis. The IIS Agent check collects metrics for active connections, bytes sent and received, request count by HTTP method, and more. It also sends a service check for each site, letting you know whether it's up or down.

# Installation

The IIS check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your IIS servers.

Also, your IIS servers must have the `Win32_PerfFormattedData_W3SVC_WebService` WMI class installed. 

# Configuration

## Prepare IIS

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

## Connect the Agent \

Create a file `iis.yaml` in the Agent's `conf.d` directory:

```
init_config:

instances:
  - host: . # "." means the current host
  # sites:  # to monitor specific sites, or to collect metrics on a per-site basis
  #   - example.com
  #   - dev.example.com
```

If you want to collect metrics on a per-site basis, you must use the `sites` option, even if you want to monitor all of your sites. When you provide `sites`, the Agent collects metrics per site and tags them with the site name — e.g. `iis.net.num_connections` tagged with `site:example.com`, and another `iis.net.num_connections` tagged with `site:dev.example.com`.

If you don't configure `sites`, the Agent collects all the same IIS metrics, but their values will reflect totals across all sites — `iis.net.num_connections` means the total number of connections on the IIS server; you will not have visibility into per-site metrics.

You can also monitor sites on remote IIS servers. See the [sample iis.conf](https://github.com/DataDog/integrations-core/blob/master/iis/conf.yaml.example) for relevant configuration options.

Restart the Agent to begin sending IIS metrics to Datadog.

# Validation

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

# Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/iis/metadata.csv) for a list of metrics provided by this integration.

# Events

# Service Checks

`iis.site_up`:

The Agent submits this service check for each configured site in `iis.yaml`. It returns `Critical` if the site's uptime is zero, otherwise `OK`.

# Further Reading
