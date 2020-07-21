# Couchbase Integration

![Couchbase Bytes Read][1]

## Overview

Identify busy buckets, track cache miss ratios, and more. This Agent check collects metrics like:

- Hard disk and memory used by data
- Current connections
- Total objects
- Operations per second
- Disk write queue size

And many more.

## Setup

### Installation

The Couchbase check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your Couchbase nodes.

### Configuration

#### Host

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

##### Metric Collection

1. Edit the `couchbase.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][3] to start collecting your Couchbase data. See the [sample couchbase.d/conf.yaml][4] for all available configuration options.

   ```yaml
   init_config:

   instances:
     ## @param server - string - required
     ## The server's url.
     #
     - server: http://localhost:8091
   ```

2. [Restart the Agent][5].

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][6] for guidance on applying the parameters below.

##### Metric collection

| Parameter            | Value                                |
| -------------------- | ------------------------------------ |
| `<INTEGRATION_NAME>` | `couchbase`                          |
| `<INIT_CONFIG>`      | blank or `{}`                        |
| `<INSTANCE_CONFIG>`  | `{"server": "http://%%host%%:8091"}` |

### Validation

[Run the Agent's `status` subcommand][8] and look for `couchbase` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][9] for a list of metrics provided by this integration.

### Events

The Couchbase check emits an event to Datadog each time the cluster rebalances.

### Service Checks

- `couchbase.can_connect`:

Returns `Critical` if the Agent cannot connect to Couchbase to collect metrics.

- `couchbase.by_node.cluster_membership`:

Returns `Critical` if the node failed over.
Returns `Warning` if the node is added to the cluster but is waiting for a rebalance.
Returns `Ok` otherwise.

- `couchbase.by_node.health`:

Returns `Critical` if the node is unhealthy. Returns `Ok` otherwise.

## Troubleshooting

Need help? Contact [Datadog support][10].

## Further Reading

- [Monitor key Couchbase metrics][11].

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/couchbase/images/couchbase_graph.png
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/couchbase/datadog_checks/couchbase/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[7]: https://docs.datadoghq.com/agent/kubernetes/log/
[8]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[9]: https://github.com/DataDog/integrations-core/blob/master/couchbase/metadata.csv
[10]: https://docs.datadoghq.com/help/
[11]: https://www.datadoghq.com/blog/monitoring-couchbase-performance-datadog
