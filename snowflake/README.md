# Agent Check: Snowflake

## Overview

This check monitors [Snowflake][1] through the Datadog Agent. Snowflake is a SaaS-analytic data warehouse and runs completely on cloud infrastructure. 
This integration monitors credit, billing, and storage usage, query history, and more.

**NOTE**: Metrics are collected via queries to Snowflake. Queries from the integration are billable by Snowflake.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host.

### Installation

The Snowflake check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `snowflake.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your snowflake performance data. See the [sample snowflake.d/conf.yaml][3] for all available configuration options.

    **Note**: By default, this integration monitors the `SNOWFLAKE` database and `ACCOUNT_USAGE` schema.
    This database is available by default and only viewable by users in the `ACCOUNTADMIN` role or [any role granted by the ACCOUNTADMIN][8].

2. [Restart the Agent][4].

### Validation

[Run the Agent's status subcommand][5] and look for `snowflake` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][6] for a list of metrics provided by this check.

### Service Checks

`snowflake.can_connect`: Returns `CRITICAL` if the Agent cannot authenticate and connect to Snowflake, `OK` otherwise.

### Events

Snowflake does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][7].

[1]: https://www.snowflake.com/
[2]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[3]: https://github.com/DataDog/integrations-core/blob/master/snowflake/datadog_checks/snowflake/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/snowflake/metadata.csv
[7]: https://docs.datadoghq.com/help/
[8]: https://docs.snowflake.com/en/sql-reference/account-usage.html#enabling-account-usage-for-other-roles
