# Agent Check: RethinkDB

## Overview

[RethinkDB][1] is a distributed documented-oriented NoSQL database, with first class support for realtime change feeds.

This check monitors a RethinkDB cluster through the Datadog Agent and collects metrics about performance, data availability, cluster configuration, and more.

**Note**: this integration is compatible with RethinkDB **version 2.3.6 and above**.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying these instructions.

### Installation

The RethinkDB check is included in the [Datadog Agent][3] package. No additional installation is needed on your server.

### Configuration

1. If using RethinkDB 2.4+, add a `datadog-agent` user with read-only permissions on the `rethinkdb` database. You can use the following ReQL commands, and refer to [Permissions and user accounts][4] for details:

    ```python
    r.db('rethinkdb').table('users').insert({'id': 'datadog-agent', 'password': '<PASSWORD>'})
    r.db('rethinkdb').grant('datadog-agent', {'read': True})
    ```

    **Note**: on RethinkDB 2.3.x, granting permissions on the `rethinkdb` database is not supported. Skip this step and use your [admin account][5] below instead.

2. Edit the `rethinkdb.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][6]. See the [sample rethinkdb.d/conf.yaml][7] for all available configuration options.

    ```yaml
    init_config:

    instances:
      - host: localhost
        port: 28015
        user: "<USER>"
        password: "<PASSWORD>"
    ```

3. [Restart the Agent][8].

**Note**: this integration collects metrics from all servers in the cluster, so you only need a single Agent.

### Validation

[Run the Agent's status subcommand][9] and look for `rethinkdb` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][10] for a list of metrics provided by this check.

### Service Checks

- `rethinkdb.can_connect`: Returns `CRITICAL` if the Agent cannot reach the configured RethinkDB server, `OK` otherwise.
- `rethinkdb.table_status.status.ready_for_outdated_reads`: Returns `OK` if all shards of a table are ready to accept outdated read queries, `WARNING` otherwise.
- `rethinkdb.table_status.status.ready_for_reads`: Returns `OK` if all shards of a table are ready to accept read queries, `WARNING` otherwise.
- `rethinkdb.table_status.status.ready_for_writes`: Returns `OK` if all shards of a table are ready to accept write queries, `WARNING` otherwise.
- `rethinkdb.table_status.status.all_replicas_ready`: Returns `OK` if all replicas are ready for reads and writes, `WARNING` otherwise (e.g. if backfills are in progress).

### Events

RethinkDB does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][11].

[1]: https://rethinkdb.com/
[2]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[3]: https://docs.datadoghq.com/agent
[4]: https://rethinkdb.com/docs/permissions-and-accounts/
[5]: https://rethinkdb.com/docs/security/#the-admin-account
[6]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[7]: https://github.com/DataDog/integrations-core/blob/master/rethinkdb/datadog_checks/rethinkdb/data/conf.yaml.example
[8]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[9]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[10]: https://github.com/DataDog/integrations-core/blob/master/rethinkdb/metadata.csv
[11]: https://docs.datadoghq.com/help
