# PgBouncer check

## Overview

The PgBouncer check tracks connection pool metrics and lets you monitor traffic to and from your application.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][1] for guidance on applying these instructions.

### Installation

The PgBouncer check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your PgBouncer nodes.

### Configuration

Edit the `pgbouncer.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][3]. See the [sample pgbouncer.d/conf.yaml][4] for all available configuration options:

```
init_config:

instances:
  - host: localhost
    port: 15433
    username: <YOUR_USERNAME>
    password: <YOUR_PASSWORD>
    # tags:
    #   - env:prod

  # Note: when the instance is configured with `database_url`, `host`, `port`, `username` and `password` are ignored.
  - database_url: postgresql://<DB_USER>:<DB_PASS>@<DB_HOST>:<DB_PORT>/dbname?sslmode=require
    # tags:
    #   - role:main
```

**Note**: `database_url` parameter value should point to PgBouncer stats database.

In your PgBouncer userlist.txt file add
```
"datadog" "<your_pass>"
```

Next, in your PgBouncer pgbouncer.ini file add
```
stats_users = datadog
```

[Restart the Agent][5] to start sending PgBouncer metrics to Datadog.

#### Log collection

**Available for Agent >6.0**

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
          service: <SERVICE_NAME>
    ```

    Change the `path` and `service` parameter values and configure them for your environment. See the [sample pgbouncer.d/conf.yaml][4] for all available configuration options.

3. [Restart the Agent][6].

### Validation

[Run the Agent's status subcommand][6] and look for `pgbouncer` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv][7] for a list of metrics provided by this check.

**Note**: Not all metrics are available with all versions of PgBouncer.

### Events
The PgBouncer check does not include any events.

### Service Checks

**pgbouncer.can_connect**:<br>
Returns `CRITICAL` if the Agent cannot connect to PgBouncer to collect metrics, otherwise returns `OK`.

## Troubleshooting
Need help? Contact [Datadog support][8].


[1]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/?tab=agentv6#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/pgbouncer/datadog_checks/pgbouncer/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/pgbouncer/metadata.csv
[8]: https://docs.datadoghq.com/help
