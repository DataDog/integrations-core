# Nfsstat Integration

## Overview

The NFS integration collects metrics about mount points on the NFS client as it uses the `nfsiostat` tool that displays NFS client per-mount [statistics][1].

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host.

### Installation

The NFSstat check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your servers.

### Configuration

Edit the `nfsstat.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][3]. Point to your nfsiostat binary script, or use the one included with the binary installer. See the [sample nfsstat.d/conf.yaml][4] for all available configuration options.

### Log collection

1. Collecting logs is disabled by default in the Datadog Agent, so to enable it in `datadog.yaml`, update this setting:

   ```yaml
   logs_enabled: true
   ```

2. Add this configuration block to your `nfsstat.d/conf.yaml` file to start collecting your NFSstat Logs:

   ```yaml
   logs:
     - type: file
       path: /var/log/messages
       source: nfsstat
   ```

   Change the `path` parameter value and configure it for your environment.
   See the [sample nfsstat.d/conf.yaml][4] for all available configuration options.

3. [Restart the Agent][5].


### Validation

[Run the Agent's `status` subcommand][6] and look for `nfsstat` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv][7] for a list of metrics provided by this check.

### Events
The Nfsstat check does not include any events.

### Service Checks
The Nfsstat check does not include any service checks.

## Troubleshooting
Need help? Contact [Datadog support][8].

## Further Reading

- [Built a network monitor on an http check][9]

[1]: http://man7.org/linux/man-pages/man8/nfsiostat.8.html
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/nfsstat/datadog_checks/nfsstat/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6v7#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/nfsstat/metadata.csv
[8]: https://docs.datadoghq.com/help/
[9]: https://docs.datadoghq.com/monitors/monitor_types/network/
