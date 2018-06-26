# Couchbase Integration

## Overview

Identify busy buckets, track cache miss ratios, and more. This Agent check collects metrics like:

* Hard disk and memory used by data
* Current connections
* Total objects
* Operations per second
* Disk write queue size

And many more.

![Couchbase Bytes Read](https://raw.githubusercontent.com/DataDog/documentation/9cca18a10dc34066a8722a23fb2cd7086ac86bd1/src/images/integrations/couchbase/couchbase_graph.png)

## Setup

### Installation

The Couchbase check is included in the [Datadog Agent](https://app.datadoghq.com/account/settings#agent) package, so you don't need to install anything else on your Couchbase nodes.

### Configuration

1. Edit the `couchbase.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your Couchbase performance data.
	See the [sample couchbase.d/conf.yaml](https://github.com/DataDog/integrations-core/blob/master/couchbase/datadog_checks/couchbase/data/conf.yaml.example) for all available configuration options.

```
init_config:

instances:
  - server: http://localhost:8091 # or wherever your Couchbase is listening
    #user: <your_username>
    #password: <your_password>
```

2. [Restart the Agent](https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent) to begin sending Couchbase metrics to Datadog.


### Validation

[Run the Agent's `status` subcommand](https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information) and look for `couchbase` under the Checks section.

## Data Collected
### Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/couchbase/metadata.csv) for a list of metrics provided by this integration.

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
Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading

* [Monitor key Couchbase metrics](https://www.datadoghq.com/blog/monitoring-couchbase-performance-datadog/).
