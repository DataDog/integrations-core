# PgBouncer check

## Overview

The PgBouncer check tracks connection pool metrics and lets you monitor traffic to and from your application.

## Setup
### Installation

The PgBouncer check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your PgBouncer nodes.

### Configuration

Create a file `pgbouncer.yaml` in the Agent's `conf.d` directory. See the [sample pgbouncer.yaml](https://github.com/DataDog/integrations-core/blob/master/pgbouncer/conf.yaml.example) for all available configuration options:

```
init_config:

instances:
  - host: localhost
    port: 15433
    username: <YOUR_USERNAME>
    password: <YOUR_PASSWORD>
#   tags:
#     - env:prod
  - database_url: postgresql://<DB_USER>:<DB_PASS>@<DB_HOST>:<DB_PORT>/dbname?sslmode=require
#   tags:
#     - role:main
```

In your PGBouncer userlist.txt file add
```
  "datadog" "<your_pass>"
```

Next, in your PGBouncer pgbouncer.ini file add
```
stats_users = datadog
```

[Restart the Agent](https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent) to start sending PgBouncer metrics to Datadog.

### Validation

[Run the Agent's `status` subcommand](https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information) and look for `pgbouncer` under the Checks section.

## Compatibility

The PgBouncer check is compatible with all major platforms.

## Data Collected
### Metrics
See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/pgbouncer/metadata.csv) for a list of metrics provided by this check.

Note: Not all metrics are available with all versions of PGBouncer.

### Events
The PGboucer check does not include any event at this time.

### Service Checks

`pgbouncer.can_connect`:

Returns CRITICAL if the Agent cannot connect to PgBouncer to collect metrics, otherwise OK.

## Troubleshooting
Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading
Learn more about infrastructure monitoring and all our integrations on [our blog](https://www.datadoghq.com/blog/)
