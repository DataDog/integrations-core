# Agent Check: Zookeeper
{{< img src="integrations/zookeeper/zookeepergraph.png" alt="Zookeeper Dashboard" responsive="true" popup="true">}}
## Overview

The Zookeeper check tracks client connections and latencies, monitors the number of unprocessed requests, and more.

## Setup
### Installation

The Zookeeper check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Zookeeper servers.


If you need the newest version of the Zookeeper check, install the `dd-check-zk` package; this package's check overrides the one packaged with the Agent. See the [integrations-core repository README.md for more details](https://github.com/DataDog/integrations-core#installing-the-integrations).

### Configuration

Create a file `zk.yaml` in the Agent's `conf.d` directory. See the [sample zk.yaml](https://github.com/DataDog/integrations-core/blob/master/zk/conf.yaml.example) for all available configuration options:

```
init_config:

instances:
  - host: localhost
    port: 2181
    timeout: 3
```

[Restart the Agent](https://docs.datadoghq.com/agent/faq/start-stop-restart-the-datadog-agent) to start sending Zookeeper metrics to Datadog.

### Validation

[Run the Agent's `status` subcommand](https://docs.datadoghq.com/agent/faq/agent-status-and-information/) and look for `zk` under the Checks section:

```
  Checks
  ======
    [...]

    zk
    -------
      - instance #0 [OK]
      - Collected 14 metrics, 0 events & 1 service check

    [...]
```

## Compatibility

The Zookeeper check is compatible with all major platforms.

## Data Collected
### Metrics

As of zookeeper 3.4.0, the `mntr` admin command is provided for easy parsing of
zookeeper stats. This check first parses the `stat` admin command for a version
number. If the zookeeper version supports `mntr`, it is also parsed.

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

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/zk/metadata.csv)
for a list of metrics provided by this check.

#### Deprecated metrics

Following metrics are still sent but will be removed eventually:
 * `zookeeper.bytes_received`
 * `zookeeper.bytes_sent`
 * `zookeeper.bytes_outstanding`

### Events
The Zookeeper check does not include any event at this time.

### Service Checks

**zookeeper.ruok**:

Returns CRITICAL if Zookeeper does not respond to the Agent's 'ruok' request, otherwise OK.

**zookeeper.mode**:

The Agent submits this service check if `expected_mode` is configured in `zk.yaml`. The check returns OK when Zookeeper's actual mode matches `expected_mode`, otherwise CRITICAL.

## Troubleshooting
Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading
Learn more about infrastructure monitoring and all our integrations on [our blog](https://www.datadoghq.com/blog/)
