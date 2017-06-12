# Cassandra Integration

# Overview

Get metrics from cassandra service in real time to:

* Visualize and monitor cassandra states
* Be notified about cassandra failovers and events.

# Installation

The Cassandra check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Cassandra nodes.

# Configuration

# Validation

Run the Agent's `info` subcommand and look for `cassandra` under the Checks section:

```
  Checks
  ======
    [...]

    cassandra
    -------
      - instance #0 [OK]
      - Collected 26 metrics, 0 events & 1 service check

    [...]
```

# Troubleshooting

# Compatibility

The cassandra check is compatible with all major platforms.

# Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/cassandra/metadata.csv) for a list of metrics provided by this integration.

# Events

# Service Checks

# Further Reading

To get a better idea of how (or why) to integrate your Cassandra cluster with Datadog, check out our [series of blog posts](https://www.datadoghq.com/blog/how-to-monitor-cassandra-performance-metrics) about it.
