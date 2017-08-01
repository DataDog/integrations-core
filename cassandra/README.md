# Cassandra Integration

# Overview

Get metrics from cassandra service in real time to:

* Visualize and monitor cassandra states
* Be notified about cassandra failovers and events.

Learn more about how to monitor Cassandra performance metrics thanks to [our series of posts](https://www.datadoghq.com/blog/how-to-monitor-cassandra-performance-metrics/). We detail the key performance metrics, how to collect them, and how to use Datadog to monitor Cassandra.
  		  
For information on JMX Checks, please see [here](http://docs.datadoghq.com/integrations/java/).
  
# Installation

The Cassandra check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Cassandra nodes.

# Configuration

To capture Cassandra metrics you need to install the Datadog Agent. Metrics will be captured using a JMX connection. 
We recommend the use of Oracle's JDK for this integration. 

This check has a limit of 350 metrics per instance. The number of returned metrics is indicated in the info page. You can specify the metrics you are interested in by editing the configuration below. To learn how to customize the metrics to collect visit the [JMX Checks documentation](https://docs.datadoghq.com/integrations/java/) for more detailed instructions. If you need to monitor more metrics, please send us an email at support@datadoghq.com

1. Configure the Agent to connect to Cassandra, just edit `conf.d/cassandra.yaml`:

```
instances:
   -    host: localhost
        port: 7199
        user: username
        password: password
        name: cassandra_instance
        #trust_store_path: /path/to/trustStore.jks # Optional, should be set if ssl is enabled
        #trust_store_password: password
        #java_bin_path: /path/to/java #Optional, should be set if the agent cannot find your java executable

# List of metrics to be collected by the integration
# Visit http://docs.datadoghq.com/integrations/java/ to customize it
init_config:
  conf:
    - include:
        domain: org.apache.cassandra.metrics
        type: ClientRequest
        scope:
          - Read
          - Write
        name:
          - Latency
          - Timeouts
          - Unavailables
        attribute:
          - Count
          - OneMinuteRate
    - include:
        domain: org.apache.cassandra.metrics
        type: ClientRequest
        scope:
          - Read
          - Write
        name:
          - TotalLatency
    - include:
        domain: org.apache.cassandra.metrics
        type: Storage
        name:
          - Load
          - Exceptions
    - include:
        domain: org.apache.cassandra.metrics
        type: ColumnFamily
        bean_regex:
          - .*keyspace=.*
        name:
          - TotalDiskSpaceUsed
          - BloomFilterDiskSpaceUsed
          - BloomFilterFalsePositives
          - BloomFilterFalseRatio
          - CompressionRatio
          - LiveDiskSpaceUsed
          - LiveSSTableCount
          - MaxRowSize
          - MeanRowSize
          - MemtableColumnsCount
          - MemtableLiveDataSize
          - MemtableSwitchCount
          - MinRowSize
      exclude:
        keyspace:
          - OpsCenter
          - system
          - system_auth
          - system_distributed
          - system_schema
          - system_traces
    - include:
        domain: org.apache.cassandra.metrics
        type: Cache
        name:
          - Capacity
          - Size
        attribute:
          - Value
    - include:
        domain: org.apache.cassandra.metrics
        type: Cache
        name:
          - Hits
          - Requests
        attribute:
          - Count
    - include:
        domain: org.apache.cassandra.metrics
        type: ThreadPools
        path: request
        name:
          - ActiveTasks
          - CompletedTasks
          - PendingTasks
          - CurrentlyBlockedTasks
    - include:
        domain: org.apache.cassandra.db
        attribute:
          - UpdateInterval
```

2. Restart the Agent

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
