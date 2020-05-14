# Agent Check: Zookeeper

![Zookeeper Dashboard][1]

## Overview

The Zookeeper check tracks client connections and latencies, monitors the number of unprocessed requests, and more.

## Setup

### Installation

The Zookeeper check is included in the [Datadog Agent][3] package, so you don't need to install anything else on your Zookeeper servers.

### Configuration

#### Zookeepr whitelist

As of version 3.5, Zookeeper has a `4lw.commands.whitelist` parameter (see [Zookeeper documentation][7]) that whitelists [four letter word commands][8]. By default, only `srvr` is whitelisted. Add `stat` and `mntr` to the whitelist, as the integration is based on these commands.

#### Host

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

1. Edit the `zk.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][4] to start collecting your Zookeeper [metrics](#metric-collection) and [logs](#log-collection).
   See the [sample zk.d/conf.yaml][5] for all available configuration options.

2. [Restart the Agent][6].

#### Log collection

_Available for Agent versions >6.0_

1. Zookeeper uses the `log4j` logger per default. To activate the logging into a file and customize the format edit the `log4j.properties` file:

   ```text
     # Set root logger level to INFO and its only appender to R
     log4j.rootLogger=INFO, R
     log4j.appender.R.File=/var/log/zookeeper.log
     log4j.appender.R.layout=org.apache.log4j.PatternLayout
     log4j.appender.R.layout.ConversionPattern=%d{yyyy-MM-dd HH:mm:ss} %-5p [%t] %c{1}:%L - %m%n
   ```

2. By default, our integration pipeline support the following conversion patterns:

   ```text
     %d{yyyy-MM-dd HH:mm:ss} %-5p %c{1}:%L - %m%n
     %d [%t] %-5p %c - %m%n
     %r [%t] %p %c %x - %m%n
   ```

    Make sure you clone and edit the integration pipeline if you have a different format.

3. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

4. Uncomment and edit this configuration block at the bottom of your `zk.d/conf.yaml`:

   ```yaml
   logs:
     - type: file
       path: /var/log/zookeeper.log
       source: zookeeper
       service: myapp
       #To handle multi line that starts with yyyy-mm-dd use the following pattern
       #log_processing_rules:
       #  - type: multi_line
       #    name: log_start_with_date
       #    pattern: \d{4}\-(0?[1-9]|1[012])\-(0?[1-9]|[12][0-9]|3[01])
   ```

    Change the `path` and `service` parameter values and configure them for your environment. See the [sample zk.d/conf.yaml][5] for all available configuration options.

5. [Restart the Agent][6].

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying the parameters below.

##### Metric collection

| Parameter            | Value                                  |
| -------------------- | -------------------------------------- |
| `<INTEGRATION_NAME>` | `zk`                                   |
| `<INIT_CONFIG>`      | blank or `{}`                          |
| `<INSTANCE_CONFIG>`  | `{"host": "%%host%%", "port": "2181"}` |

##### Log collection

_Available for Agent versions >6.0_

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes log collection documentation][12].

| Parameter      | Value                                           |
| -------------- | ----------------------------------------------- |
| `<LOG_CONFIG>` | `{"source": "zookeeper", "service": "<SERVICE_NAME>"}` |

### Validation

[Run the Agent's status subcommand][9] and look for `zk` under the Checks section.

## Data Collected

### Metrics

As of zookeeper 3.4.0, the `mntr` admin command is provided for easy parsing of zookeeper stats. This check first parses the `stat` admin command for a version number. If the zookeeper version supports `mntr`, it is also parsed.

Duplicate information is being reported by both `mntr` and `stat`: the duplicated
`stat` metrics are only kept for backward compatibility.

**Important:** if available, make use of the data reported by `mntr`, not `stat`.

| Metric reported by `mntr`         | Duplicate reported by `stat` |
| --------------------------------- | ---------------------------- |
| `zookeeper.avg_latency`           | `zookeeper.latency.avg`      |
| `zookeeper.max_latency`           | `zookeeper.latency.max`      |
| `zookeeper.min_latency`           | `zookeeper.latency.min`      |
| `zookeeper.packets_received`      | `zookeeper.packets.received` |
| `zookeeper.packets_sent`          | `zookeeper.packets.sent`     |
| `zookeeper.num_alive_connections` | `zookeeper.connections`      |
| `zookeeper.znode_count`           | `zookeeper.nodes`            |

See [metadata.csv][10] for a list of metrics provided by this check.

#### Deprecated metrics

Following metrics are still sent but will be removed eventually:

- `zookeeper.bytes_received`
- `zookeeper.bytes_sent`

### Events

The Zookeeper check does not include any events.

### Service Checks

**zookeeper.ruok**:<br>
Sends `ruok` to the monitored node. Returns `OK` with an `imok` response, `WARN` in the case of a different response and `CRITICAL` if no response is received..

**zookeeper.mode**:<br>
The Agent submits this service check if `expected_mode` is configured in `zk.yaml`. The check returns `OK` when Zookeeper's actual mode matches `expected_mode`, otherwise returns `CRITICAL`.

## Troubleshooting

Need help? Contact [Datadog support][11].

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/zk/images/zk_dashboard.png
[2]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[3]: https://app.datadoghq.com/account/settings#agent
[4]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[5]: https://github.com/DataDog/integrations-core/blob/master/zk/datadog_checks/zk/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[7]: https://zookeeper.apache.org/doc/r3.5.4-beta/zookeeperAdmin.html#sc_clusterOptions
[8]: https://zookeeper.apache.org/doc/r3.5.4-beta/zookeeperAdmin.html#sc_4lw
[9]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[10]: https://github.com/DataDog/integrations-core/blob/master/zk/metadata.csv
[11]: https://docs.datadoghq.com/help/
[12]: https://docs.datadoghq.com/agent/kubernetes/log/
