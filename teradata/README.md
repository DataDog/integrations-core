# Agent Check: Teradata

## Overview

This check monitors [Teradata][1] through the Datadog Agent.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The Teradata check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

#### Prepare Teradata

1. Download and install the [Teradata JDBC Driver][10] for your system from the Teradata downloads page.
2. Create a read-only `datadog` user with proper access to your Teradata Database. Start a `BTEQ` session on your Teradata Database:

```shell
CREATE USER "datadog" AS PASSWORD="<PASSWORD>";
```

Optional, but recommended: Create and/or grant a role to the `datadog` user designated for read-only monitoring purposes. 

```shell
GRANT "<READ_ONLY_ROLE>" TO "datadog"; 
```

The Teradata system grants the `SELECT` privilege to PUBLIC on most [Data Dictionary views][11] by default. All Teradata Database users have `PUBLIC` privileges.

3. To collect resource usage metrics, enable the [SPMA Resource Usage Table][12]. This can be done using the [`ctl` Teradata Utility][13]:

```shell
# Start ctl session
ctl

# View RSS screen
screen rss

# Enable SPMA resource usage table
SPMA=yes

# Save the configuration setting
write
```

Note: The SPMA Resource Table logs statistics every 10 minutes by default. This can be configured in the `rss` screen using `ctl`. Resource Usage logging may impact database performance. To reduce the frequency of Resource Usage logging, increase the logging interval of the `Node Logging Rate` setting. See the Teradata [documentation][14] for more information on Resource Usage Logging.


### Configuration

1. Edit the `teradata.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your teradata performance data. See the [sample teradata.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `teradata` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this check.

### Events

The Teradata integration does not include any events.

### Service Checks

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: https://www.teradata.com/
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/check/datadog_checks/teradata/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/check/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/check/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://downloads.teradata.com/download/connectivity/jdbc-driver
[11]: https://docs.teradata.com/r/Teradata-VantageTM-Data-Dictionary/July-2021/Data-Dictionary-Views/Access-to-Data-Dictionary-Views/Default-PUBLIC-Privileges-for-Views
[12]: https://docs.teradata.com/r/Teradata-VantageTM-Resource-Usage-Macros-and-Tables/July-2021/ResUsageSpma-Table
[13]: https://docs.teradata.com/r/Teradata-VantageTM-Database-Utilities/July-2021/Control-GDO-Editor-ctl/Ctl-Commands/SCREEN
[14]: https://docs.teradata.com/r/Teradata-VantageTM-Resource-Usage-Macros-and-Tables/July-2021/Planning-Your-Resource-Usage-Data/Resource-Usage-Logging