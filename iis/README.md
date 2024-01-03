# IIS Integration

![IIS Graph][1]

## Overview

Collect IIS metrics aggregated across all of your sites, or on a per-site basis. The IIS Agent check collects metrics for active connections, bytes sent and received, request count by HTTP method, and more. It also sends a service check for each site, letting you know whether it's up or down.

## Setup

### Installation

The IIS check is packaged with the Agent. To start gathering your IIS metrics and logs, [install the Agent][2] on your IIS servers.

#### Host

To configure this check for an Agent running on a host:

##### Metric collection

1. Edit the `iis.d/conf.yaml` file in the [Agent's `conf.d` directory][3] at the root of your [Agent's configuration directory][4] to start collecting your IIS site data. See the [sample iis.d/conf.yaml][5] for all available configuration options.

2. [Restart the Agent][6] to begin sending IIS metrics to Datadog.

**Note**: Versions 2.14.0 or later of this check use a new implementation for metric collection, which requires Python 3. For hosts that are unable to use Python 3, or if you would like to use a legacy version of this check, refer to the following [config][11].

##### Log collection

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
   ```

    Change the `path` and `service` parameter values and configure them for your environment. See the [sample iis.d/conf.yaml][5] for all available configuration options.

3. [Restart the Agent][6].

**Note**: Ensure the `datadog-agent` user has read and execute access to tail the log files you want to collect from. When IIS creates a new sub-folder (such as when a new site is created), the permissions of the parent folder are not automatically inherited. See [Permission issues tailing log files][12] for more information.


### Validation

[Run the Agent's status subcommand][7] and look for `iis` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][8] for a list of metrics provided by this integration.

### Events

The IIS check does not include any events.

### Service Checks

See [service_checks.json][9] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][10].


[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/iis/images/iisgraph.png
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/basic_agent_usage/windows/#agent-check-directory-structure
[4]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[5]: https://github.com/DataDog/integrations-core/blob/master/iis/datadog_checks/iis/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/iis/metadata.csv
[9]: https://github.com/DataDog/integrations-core/blob/master/iis/assets/service_checks.json
[10]: https://docs.datadoghq.com/help/
[11]: https://github.com/DataDog/integrations-core/blob/7.33.x/iis/datadog_checks/iis/data/conf.yaml.example
[12]: https://docs.datadoghq.com/logs/guide/log-collection-troubleshooting-guide/#permission-issues-tailing-log-files
