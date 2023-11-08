# Agent Check: RethinkDB

## Overview

[RethinkDB][1] is a distributed documented-oriented NoSQL database, with first class support for realtime
change feeds.

This check monitors a RethinkDB cluster through the Datadog Agent and collects metrics about performance,
data availability, cluster configuration, and more.

**Note**: this integration is compatible with RethinkDB **version 2.3.6 and above**.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For
containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying these
instructions.

### Installation

The RethinkDB check is included in the [Datadog Agent][3] package. No additional installation is needed on your server.

### Configuration

1. If using RethinkDB 2.4+, add a `datadog-agent` user with read-only permissions on the `rethinkdb`
database. You can use the following ReQL commands, and see [Permissions and user accounts][4] for
details:

    ```python
    r.db('rethinkdb').table('users').insert({'id': 'datadog-agent', 'password': '<PASSWORD>'})
    r.db('rethinkdb').grant('datadog-agent', {'read': True})
    ```

    **Note**: on RethinkDB 2.3.x, granting permissions on the `rethinkdb` database is not supported. Skip
    this step and use your [admin account][5] below instead.

2. Edit the `rethinkdb.d/conf.yaml` file in the `conf.d/` folder at the root of your
[Agent's configuration directory][6]. See the [sample rethinkdb.d/conf.yaml][7] for all available
configuration options.

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

#### Log collection


1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

    ```yaml
    logs_enabled: true
    ```

2. Edit this configuration block in your `rethinkdb.d/conf.yaml` file to start collecting your RethinkDB logs:

    ```yaml
    logs:
      - type: file
        path: "<LOG_FILE_PATH>"
        source: rethinkdb
        service: "<SERVICE_NAME>"
    ```


    Change the `path` parameter value based on your environment. See the [sample conf.yaml][7] for all available configuration options.

3. [Restart the Agent][8].

To enable logs for Kubernetes environments, see [Kubernetes Log Collection][9].

### Validation

[Run the Agent's status subcommand][10] and look for `rethinkdb` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][11] for a list of metrics provided by this check.

### Events

RethinkDB does not include any events.

### Service Checks

See [service_checks.json][12] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][13].


[1]: https://rethinkdb.com
[2]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[3]: https://app.datadoghq.com/account/settings/agent/latest
[4]: https://rethinkdb.com/docs/permissions-and-accounts/
[5]: https://rethinkdb.com/docs/security/#the-admin-account
[6]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[7]: https://github.com/DataDog/integrations-core/blob/master/rethinkdb/datadog_checks/rethinkdb/data/conf.yaml.example
[8]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[9]: https://docs.datadoghq.com/agent/kubernetes/log/
[10]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[11]: https://github.com/DataDog/integrations-core/blob/master/rethinkdb/metadata.csv
[12]: https://github.com/DataDog/integrations-core/blob/master/rethinkdb/assets/service_checks.json
[13]: https://docs.datadoghq.com/help/
