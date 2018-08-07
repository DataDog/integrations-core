# PgBouncer check

## Overview

The PgBouncer check tracks connection pool metrics and lets you monitor traffic to and from your application.

## Setup
### Installation

The PgBouncer check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your PgBouncer nodes.

### Configuration

To capture PGBouncer metrics you need to install the Datadog Agent on your PGBouncer server.

1. Create a read-only datadog user with proper access to your PostgreSQL Server. Start psql on your PostgreSQL database and run:

    ```
    CREATE USER datadog WITH PASSWORD '<YOUR_PASSWORD>';
    GRANT SELECT ON pg_stat_database TO datadog;
    ```

    Check if the datadog user has been correctly created with this command:
    
    ```
    psql -h localhost -U datadog postgres -c "SELECT * FROM pg_stat_database LIMIT(1);"  <br/> && \
    echo -e "\e[0;32mPostgres connection - OK\e[0m" || \ ||  <br/>echo -e "\e[0;31mCannot connect to Postgres\e[0m"
    ```

    When prompted for a password, enter your `<YOUR_PASSWORD>`.

2. In your PGBouncer `userlist.txt` file add:
  
    ```
    "datadog" "<YOUR_PASSWORD>"
    ```

3. In your PGBouncer `pgbouncer.ini` file add `datadog` as `stats_user`​ or `admin_user`, for example:

    ```
    stats_users = datadog
    ```

4. Configure the Agent to connect to PGBouncer: 
  Edit the `pgbouncer.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][7]. 
  See the [sample pgbouncer.d/conf.yaml][2] for all available configuration options:

    ```
      init_config:

      instances:
        - host: localhost
          port: 15433
          username: <YOUR_USERNAME>
          password: <YOUR_PASSWORD>
          tags:
            - optional_tag1
            - optional_tag2
        - database_url: postgresql://user:pass@host:5432/dbname?sslmode=require
          tags:
            - optional_tag3
            - optional_tag4  
    ```

    **Note**: `database_url` parameter value should point to PgBouncer stats database.

5. [Restart the Agent][3] to start sending PgBouncer metrics to Datadog.

### Validation

[Run the Agent's `status` subcommand][4] and look for `pgbouncer` under the Checks section.

## Data Collected
### Metrics

See [metadata.csv][5] for a list of metrics provided by this check.

Note: Not all metrics are available with all versions of PgBouncer.

### Events
The PgBouncer check does not include any events at this time.

### Service Checks

`pgbouncer.can_connect`:

Returns CRITICAL if the Agent cannot connect to PgBouncer to collect metrics, otherwise OK.

## Troubleshooting
Need help? Contact [Datadog Support][6].

[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/pgbouncer/datadog_checks/pgbouncer/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/pgbouncer/metadata.csv
[6]: https://docs.datadoghq.com/help/
[7]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
