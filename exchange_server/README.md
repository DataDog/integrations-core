# Microsoft Exchange Server Integration

## Overview

Get metrics from Microsoft Exchange Server

- Visualize and monitor Exchange server performance

## Setup

### Installation

The Exchange check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your servers.

### Configuration

1. Edit the `exchange_server.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][2] to start collecting your Exchange Server performance data.

2. [Restart the Agent][3].

**Note**: Versions 1.11.0 or later of this check use a new implementation for metric collection, which requires Python 3. For hosts that are unable to use Python 3, or if you would like to use a legacy version of this check, refer to the following [config][8].

### Log collection

1. Collecting logs is disabled by default in the Datadog Agent, you need to enable it in `datadog.yaml`:

   ```yaml
   logs_enabled: true
   ```

2. Add this configuration block to your `exchange_server.d/conf.yaml` file to start collecting your Exchange Server Logs:

   ```yaml
   logs:
     - type: file
       path: "C:\\Program Files\\Microsoft\\Exchange Server\\V15\\TransportRoles\\Logs\\CommonDiagnosticsLog\\*"
       source: exchange-server
     - type: file
       path: "C:\\Program Files\\Microsoft\\Exchange Server\\V15\\TransportRoles\\Logs\\ThrottlingService\\*"
       source: exchange-server
     - type: file
       path: "C:\\Program Files\\Microsoft\\Exchange Server\\V15\\TransportRoles\\Logs\\Hub\\Connectivity\\*"
       source: exchange-server
   ```
    **Note**: The only logs supported are CommonDiagnosticsLog, ThrottlingService, and Connectivity logs due to Exchange Server outputting many different types of logs. Contact [Datadog support][7] to request other logs formats.

   Change the `path` parameter value and configure it for your environment.
   See the [sample exchange_server.d/conf.yaml][4] for all available configuration options.

3. [Restart the Agent][3].


### Validation

[Run the Agent's status subcommand][5] and look for `exchange_server` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][6] for a list of metrics provided by this integration.

### Events

The Exchange server check does not include any events.

### Service Checks

The Exchange server check does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][7].

[1]: https://app.datadoghq.com/account/settings/agent/latest
[2]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[3]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[4]: https://github.com/DataDog/integrations-core/blob/master/exchange_server/datadog_checks/exchange_server/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/exchange_server/metadata.csv
[7]: https://docs.datadoghq.com/help/
[8]: https://github.com/DataDog/integrations-core/blob/7.33.x/exchange_server/datadog_checks/exchange_server/data/conf.yaml.example
