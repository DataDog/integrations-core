# Agent Check: ProxySQL

## Overview

This check monitors [ProxySQL][1] through the Datadog Agent.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying these instructions.

### Installation

The ProxySQL integration is included in the [Datadog Agent][3] package, so you don't need to install anything else on your servers.

### Configuration

#### Host

1. Edit the `proxysql.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][4] to start collecting your ProxySQL performance data. See the [sample proxysql.d/conf.yaml][5] for all available configuration options.

2. [Restart the Agent][6].

##### Log Collection

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

2. Add the log files you are interested in to your `proxysql.d/conf.yaml` file to start collecting your ProxySQL logs:

   ```yaml
     logs:
         # Default logging file
       - type: file
         path: /var/log/proxysql.log
         source: proxysql
         service: "<SERVICE_NAME>"
         # Logged queries, file needs to be in JSON
         # https://github.com/sysown/proxysql/wiki/Query-Logging
       - type: file
         path: "<QUERY_LOGGING_FILE_PATH>"
         source: proxysql
         service: "<SERVICE_NAME>"
         # Audit log
         # https://github.com/sysown/proxysql/wiki/Audit-log
       - type: file
         path: "<AUDIT_LOG_FILE_PATH>"
         source: proxysql
         service: "<SERVICE_NAME>"
   ```

    Change the `path` and `service` parameter values and configure them for your environment. See the [sample proxysql.d/conf.yaml][5] for all available configuration options.

3. [Restart the Agent][6].

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying the parameters below.

#### Metric Collection

| Parameter            | Value                                                      |
|----------------------|------------------------------------------------------------|
| `<INTEGRATION_NAME>` | `proxysql`                                                   |
| `<INIT_CONFIG>`      | blank or `{}`                                              |
| `<INSTANCE_CONFIG>`  | `{"host": "%%host%%", "port": "%%port%%", "username": "<USER>", "password": "<PASSWORD>"}`       |

##### Log collection

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Docker log collection][9].

| Parameter      | Value                                     |
|----------------|-------------------------------------------|
| `<LOG_CONFIG>` | `{"source": "proxysql", "service": "<SERVICE_NAME>"}` |


### Validation

[Run the Agent's status subcommand][7] and look for `proxysql` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][8] for a list of metrics provided by this check.

### Service Checks

`proxysql.can_connect`: Returns `CRITICAL` if the Agent can't connect to ProxySQL, otherwise returns `OK`. This service check is tagged by `server` and `port`

`proxysql.backend.status`: Returns `CRITICAL` if ProxySQL considers the backend host as SHUNNED or OFFLINE_HARD. Returns `WARNING` if the backend host is `OFFLINE_SOFT`. Returns `OK` otherwise. This service check is tagged by `hostgroup`, `srv_host` and `srv_port`.

### Events

The ProxySQL check does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][7].

[1]: https://proxysql.com/
[2]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[3]: https://docs.datadoghq.com/agent
[4]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[5]: https://github.com/DataDog/integrations-core/blob/master/proxysql/datadog_checks/proxysql/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/proxysql/metadata.csv
[9]: https://docs.datadoghq.com/agent/docker/log
[10]: https://docs.datadoghq.com/help
