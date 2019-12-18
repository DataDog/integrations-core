# Couchbase Integration

![Couchbase Bytes Read][1]

## Overview

Identify busy buckets, track cache miss ratios, and more. This Agent check collects metrics like:

* Hard disk and memory used by data
* Current connections
* Total objects
* Operations per second
* Disk write queue size

And many more.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying these instructions.

### Installation

The Couchbase check is included in the [Datadog Agent][3] package, so you don't need to install anything else on your Couchbase nodes.

### Configuration

1. Edit the `couchbase.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][4] to start collecting your Couchbase performance [metrics](#metric-collection) and [logs](#log-collection).
  See the [sample couchbase.d/conf.yaml][5] for all available configuration options.

#### Metric Collection

1.  Add this configuration block to your `couchbase.d/conf.yaml` file to start gathering your [Couchbase Metrics](#metrics):

      ```
      init_config:

      instances:
        - server: http://localhost:8091 # or wherever your Couchbase is listening
          #username: <your_username>
          #password: <your_password>
      ```

2. [Restart the Agent][6] to begin sending Couchbase metrics to Datadog.

#### Log collection

**Available for Agent >6.0**

1. Collecting logs is disabled by default in the Datadog Agent, you need to enable it in `datadog.yaml`:

    ```yaml
      logs_enabled: true
    ```

2. Add this configuration block to your `couchbase.d/conf.yaml` file to start collecting your Apache Logs:

    ```yaml
      logs:
          - type: file
            path: /var/log/couchdb/couch.log
            source: couchdb
            service: couchbase
    ```

    Change the `path` and `service` parameter values and configure them for your environment.
    See the [sample couchbase.d/conf.yaml][5] for all available configuration options.

3. [Restart the Agent][6].


### Validation

[Run the Agent's `status` subcommand][7] and look for `couchbase` under the Checks section.

## Data Collected
### Metrics

See [metadata.csv][8] for a list of metrics provided by this integration.

### Events

The Couchbase check emits an event to Datadog each time the cluster rebalances.

### Service Checks

- `couchbase.can_connect`:

Returns `Critical` if the Agent cannot connect to Couchbase to collect metrics.

- `couchbase.by_node.cluster_membership`:

Returns `Critical` if the node failed over.
Returns `Warning` if the node is added to the cluster but is waiting for a rebalance.
Returns `Ok` otherwise.

- `couchbase.by_node.health_status`:

Returns `Critical` if the node is unhealthy. Returns `Ok` otherwise.

## Troubleshooting
Need help? Contact [Datadog support][9].

## Further Reading

* [Monitor key Couchbase metrics][10].


[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/couchbase/images/couchbase_graph.png
[2]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[3]: https://app.datadoghq.com/account/settings#agent
[4]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[5]: https://github.com/DataDog/integrations-core/blob/master/couchbase/datadog_checks/couchbase/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/couchbase/metadata.csv
[9]: https://docs.datadoghq.com/help
[10]: https://www.datadoghq.com/blog/monitoring-couchbase-performance-datadog
