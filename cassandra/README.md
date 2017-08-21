# Cassandra Integration

## Overview

Get metrics from cassandra service in real time to:

* Visualize and monitor cassandra states
* Be notified about cassandra failovers and events.

## Setup
### Installation

The Cassandra check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Cassandra nodes.

### Configuration

No configuration steps are required for the Cassandra check at this time

### Validation

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

## Compatibility

The cassandra check is compatible with all major platforms.

## Data Collected
### Metrics
See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/cassandra/metadata.csv) for a list of metrics provided by this integration.

### Events
The Cassandra check does not include any event at this time.

### Service Checks
The Cassandra check does not include any service check at this time.

## Troubleshooting

## Further Reading
### Blog Article
To get a better idea of how (or why) to integrate your Cassandra cluster with Datadog, check out our [series of blog posts](https://www.datadoghq.com/blog/how-to-monitor-cassandra-performance-metrics) about it.
