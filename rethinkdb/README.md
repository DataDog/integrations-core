# Agent Check: RethinkDB

## Overview

[RethinkDB](https://rethinkdb.com) is a distributed documented-oriented NoSQL database, with first class support for realtime
change feeds.

This check monitors a RethinkDB cluster through the Datadog Agent and collects metrics about performance,
data availability, cluster configuration, and more.

**Note**: this integration is compatible with RethinkDB **version 2.3.6 and above**.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For
containerized environments, see the [Autodiscovery Integration Templates](https://docs.datadoghq.com/agent/kubernetes/integrations/) for guidance on applying these
instructions.

### Installation

The RethinkDB check is included in the [Datadog Agent](https://docs.datadoghq.com/agent/) package. No additional installation is needed on your server.

### Configuration

1. If using RethinkDB 2.4+, add a `datadog-agent` user with read-only permissions on the `rethinkdb`
database. You can use the following ReQL commands, and refer to [Permissions and user accounts](https://rethinkdb.com/docs/permissions-and-accounts/) for
details:

    ```python
    r.db('rethinkdb').table('users').insert({'id': 'datadog-agent', 'password': '<PASSWORD>'})
    r.db('rethinkdb').grant('datadog-agent', {'read': True})
    ```

    **Note**: on RethinkDB 2.3.x, granting permissions on the `rethinkdb` database is not supported. Skip
    this step and use your [admin account](https://rethinkdb.com/docs/security/#the-admin-account) below instead.

2. Edit the `rethinkdb.d/conf.yaml` file in the `conf.d/` folder at the root of your
[Agent's configuration directory](https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory). See the [sample rethinkdb.d/conf.yaml](https://github.com/DataDog/integrations-core/blob/master/rethinkdb/datadog_checks/rethinkdb/data/conf.yaml.example) for all available
configuration options.

    ```yaml
    init_config:

    instances:
      - host: localhost
        port: 28015
        user: "<USER>"
        password: "<PASSWORD>"
    ```

3. [Restart the Agent](https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent).

**Note**: this integration collects metrics from all servers in the cluster, so you only need a single Agent.

#### Log Collection

_Available for Agent versions >6.0_

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

  ```yaml
  logs_enabled: true
  ```

2. Add this configuration block to your `rethinkdb.d/conf.yaml` file to start collecting your RethinkDB logs:

  ```yaml
logs:
  - type: file
    path: "<LOG_FILE_PATH>"
    source: rethinkdb
    service: "<SERVICE_NAME>"
```


  Change the `path` and `service` parameter values based on your environment. See the https://github.com/DataDog/integrations-core/blob/master/rethinkdb/datadog_checks/rethinkdb/data/conf.yaml.example for all available configuration options.

  3. [Restart the Agent](https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent).

  See [Datadog's documentation](https://docs.datadoghq.com/agent/kubernetes/log/) for additional information on how to configure the Agent for log collection in Kubernetes environments.

### Validation

[Run the Agent's status subcommand](https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information) and look for `rethinkdb` under the Checks section.

## Data Collected



### Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/rethinkdb/metadata.csv) for a list of metrics provided by this check.

### Service Checks

**rethinkdb.can_connect**:<br>
Returns `CRITICAL` if the Agent cannot reach the configured RethinkDB server, `OK` otherwise.

**rethinkdb.table_status.status.ready_for_outdated_reads**:<br>
Returns `OK` if all shards of a table are ready to accept outdated read queries, `WARNING` otherwise.

**rethinkdb.table_status.status.ready_for_reads**:<br>
Returns `OK` if all shards of a table are ready to accept read queries, `WARNING` otherwise.

**rethinkdb.table_status.status.ready_for_writes**:<br>
Returns `OK` if all shards of a table are ready to accept write queries, `WARNING` otherwise.

**rethinkdb.table_status.status.all_replicas_ready**:<br>
Returns `OK` if all replicas are ready for reads and writes, `WARNING` otherwise (e.g. if backfills are in progress).


### Events

RethinkDB does not include any events.

## Troubleshooting

Need help? Contact [Datadog support](https://docs.datadoghq.com/help/).
