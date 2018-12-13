# PgBouncer check

## Overview

The PgBouncer check tracks connection pool metrics and lets you monitor traffic to and from your application.

## Setup
### Installation

The PgBouncer check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your PgBouncer nodes.

### Configuration

Edit the `pgbouncer.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][2]. See the [sample pgbouncer.d/conf.yaml][3] for all available configuration options:

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

[Restart the Agent][4] to start sending PgBouncer metrics to Datadog.

### Validation

[Run the Agent's `status` subcommand][5] and look for `pgbouncer` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv][6] for a list of metrics provided by this check.

Note: Not all metrics are available with all versions of PgBouncer.

### Events
The PgBouncer check does not include any events at this time.

### Service Checks

`pgbouncer.can_connect`:

Returns CRITICAL if the Agent cannot connect to PgBouncer to collect metrics, otherwise OK.

## Troubleshooting
Need help? Contact [Datadog Support][7].

[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
[3]: https://github.com/DataDog/integrations-core/blob/master/pgbouncer/datadog_checks/pgbouncer/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[5]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/pgbouncer/metadata.csv
[7]: https://docs.datadoghq.com/help
