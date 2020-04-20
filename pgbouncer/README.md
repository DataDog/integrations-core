# PgBouncer check

## Overview

The PgBouncer check tracks connection pool metrics and lets you monitor traffic to and from your application.

## Setup

### Installation

The PgBouncer check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your PgBouncer nodes.

This check needs an associated user to query your PgBouncer instance:

1. Create a Datadog user in your PgBouncer `pgbouncer.ini` file:

   ```ini
   stats_users = datadog
   ```

2. Add an associated password for the `datadog` user in your PgBouncer `userlist.txt` file:

   ```text
   "datadog" "<PASSWORD>"
   ```

### Configuration

#### Host

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

##### Metric collection

1. Edit the `pgbouncer.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][2]. See the [sample pgbouncer.d/conf.yaml][3] for all available configuration options:

   ```yaml
   init_config:

   instances:
     ## @param database_url - string - required
     ## `database_url` parameter should point to PgBouncer stats database url
     #
     - database_url: "postgresql://datadog:<PASSWORD>@<HOSTNAME>:<PORT>/<DATABASE_URL>?sslmode=require"
   ```

2. [Restart the Agent][4].

##### Log collection

_Available for Agent versions >6.0_

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

2. Add this configuration block to your `pgbouncer.d/conf.yaml` file to start collecting your Pgbouncer logs:

   ```yaml
   logs:
     - type: file
       path: /var/log/postgresql/pgbouncer.log
       source: pgbouncer
       service: "<SERVICE_NAME>"
   ```

    Change the `path` and `service` parameter values and configure them for your environment. See the [sample pgbouncer.d/conf.yaml][3] for all available configuration options.

3. [Restart the Agent][5].

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][6] for guidance on applying the parameters below.

##### Metric collection

| Parameter            | Value                                                                                                  |
| -------------------- | ------------------------------------------------------------------------------------------------------ |
| `<INTEGRATION_NAME>` | `oracle`                                                                                               |
| `<INIT_CONFIG>`      | blank or `{}`                                                                                          |
| `<INSTANCE_CONFIG>`  | `{"database_url": "postgresql://datadog:<PASSWORD>@%%host%%:%%port%%/<DATABASE_URL>?sslmode=require"}` |

##### Log collection

_Available for Agent versions >6.0_

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes log collection documentation][7].

| Parameter      | Value                                           |
| -------------- | ----------------------------------------------- |
| `<LOG_CONFIG>` | {"source": "pgbouncer", "service": "pgbouncer"} |

### Validation

[Run the Agent's status subcommand][5] and look for `pgbouncer` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][8] for a list of metrics provided by this check.

**Note**: Not all metrics are available with all versions of PgBouncer.

### Events

The PgBouncer check does not include any events.

### Service Checks

**pgbouncer.can_connect**:<br>
Returns `CRITICAL` if the Agent cannot connect to PgBouncer to collect metrics, otherwise returns `OK`.

## Troubleshooting

Need help? Contact [Datadog support][9].

[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[3]: https://github.com/DataDog/integrations-core/blob/master/pgbouncer/datadog_checks/pgbouncer/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[6]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[7]: https://docs.datadoghq.com/agent/kubernetes/log/
[8]: https://github.com/DataDog/integrations-core/blob/master/pgbouncer/metadata.csv
[9]: https://docs.datadoghq.com/help
