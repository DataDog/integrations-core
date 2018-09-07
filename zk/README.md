# Agent Check: Zookeeper

![Zookeeper Dashboard][20]

## Overview

The Zookeeper check tracks client connections and latencies, monitors the number of unprocessed requests, and more.

## Setup
### Installation

The Zookeeper check is included in the [Datadog Agent][13] package, so you don't need to install anything else on your Zookeeper servers.

### Configuration

1. Edit the `zk.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][21] to start collecting your Zookeeper [metrics](#metric-collection) and [logs](#log-collection).
  See the [sample zk.d/conf.yaml][14] for all available configuration options.

2. [Restart the Agent][15]

### Zookeepr Whitelist
As of version 3.5, Zookeeper has a `4lw.commands.whitelist` parameter (see [Zookeeper documentation][22]) that whitelists [4 letter word commands][23]. By default, only `srvr` is whitelisted. Add `stat` and `mntr` to the whitelist, as the integration is based on these commands.

#### Metric Collection

*  Add this configuration block to your `zk.yaml` file to start gathering your [Zookeeper metrics](#metrics):

```
init_config:

instances:
  - host: localhost
    port: 2181
    timeout: 3
```

* See the [sample zk.yaml][14] for all available configuration options.

* [Restart the Agent][15] to start sending Zookeeper metrics to Datadog.

#### Log Collection

**Available for Agent >6.0**

Zookeeper uses the `log4j` logger per default. To activate the logging into a file and customize the format edit the `log4j.properties` file:

```
 # Set root logger level to INFO and its only appender to R
log4j.rootLogger=INFO, R
log4j.appender.R.File=/var/log/zookeeper.log
log4j.appender.R.layout=org.apache.log4j.PatternLayout
log4j.appender.R.layout.ConversionPattern=%d{yyyy-MM-dd HH:mm:ss} %-5p [%t] %c{1}:%L - %m%n
```

By default, our integration pipeline support the following conversion patterns:

  ```
  %d{yyyy-MM-dd HH:mm:ss} %-5p %c{1}:%L - %m%n
  %d [%t] %-5p %c - %m%n
  %r [%t] %p %c %x - %m%n
  ```

Make sure you clone and edit the integration pipeline if you have a different format.

* Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file with:

  ```
  logs_enabled: true
  ```

* Add this configuration block to your `zk.yaml` file to start collecting your Zookeeper Logs:

  ```
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

* See the [sample zk.yaml][14] for all available configuration options.

* [Restart the Agent][15] to start sending Zookeeper Logs to Datadog.

### Validation

[Run the Agent's `status` subcommand][16] and look for `zk` under the Checks section.

## Data Collected
### Metrics

As of zookeeper 3.4.0, the `mntr` admin command is provided for easy parsing of zookeeper stats. This check first parses the `stat` admin command for a version number. If the zookeeper version supports `mntr`, it is also parsed.

Duplicate information is being reported by both `mntr` and `stat`: the duplicated
 `stat` metrics are only kept for backward compatibility.

**Important:** if available, make use of the data reported by `mntr`, not `stat`.

| Metric reported by `mntr` | Duplicate reported by `stat` |
| ------------------------- | ---------------------------- |
| `zookeeper.avg_latency` | `zookeeper.latency.avg` |
| `zookeeper.max_latency` | `zookeeper.latency.max` |
| `zookeeper.min_latency` | `zookeeper.latency.min` |
| `zookeeper.packets_received` | `zookeeper.packets.received` |
| `zookeeper.packets_sent` | `zookeeper.packets.sent` |
| `zookeeper.num_alive_connections` | `zookeeper.connections` |
| `zookeeper.znode_count` | `zookeeper.nodes` |

See [metadata.csv][17]
for a list of metrics provided by this check.

#### Deprecated metrics

Following metrics are still sent but will be removed eventually:
 * `zookeeper.bytes_received`
 * `zookeeper.bytes_sent`
 * `zookeeper.bytes_outstanding`

### Events
The Zookeeper check does not include any events at this time.

### Service Checks

**zookeeper.ruok**:

Sends `ruok` to the monitored node. Returns `OK` with an `imok` response, `WARN` in the case of a different response and `CRITICAL` if no response is received..

**zookeeper.mode**:

The Agent submits this service check if `expected_mode` is configured in `zk.yaml`. The check returns `OK` when Zookeeper's actual mode matches `expected_mode`, otherwise `CRITICAL`.

## Troubleshooting
Need help? Contact [Datadog Support][18].

[13]: https://app.datadoghq.com/account/settings#agent
[14]: https://github.com/DataDog/integrations-core/blob/master/zk/datadog_checks/zk/data/conf.yaml.example
[15]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[16]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[17]: https://github.com/DataDog/integrations-core/blob/master/zk/metadata.csv
[18]: https://docs.datadoghq.com/help/
[20]: https://raw.githubusercontent.com/DataDog/integrations-core/master/zk/images/zk_dashboard.png
[21]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
[22]: https://zookeeper.apache.org/doc/r3.5.4-beta/zookeeperAdmin.html#sc_clusterOptions
[23]: https://zookeeper.apache.org/doc/r3.5.4-beta/zookeeperAdmin.html#sc_4lw
