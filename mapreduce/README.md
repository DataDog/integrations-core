# Mapreduce Check

# Overview

The Hadoop Mapreduce check lets you monitor the status and duration of map and reduce tasks.

To collect other Hadoop-related metrics, see the hdfs_datanode, hdfs_namenode, and yarn checks.

# Installation

The Agent's Mapreduce check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Hadoop cluster's master nodes. If you need the newest version of the check, install the `dd-check-mapreduce` package.

# Configuration

Create a file `mapreduce.yaml` in the Agent's `conf.d` directory:

```
instances:
  # The Mapreduce check collects metrics from YARN's ResourceManager. Run the 
  # check on your master node and specify the ResourceManager URI below.
  # If you don't know your ResourceManager's port, you can find it in the 
  # yarn-site.xml conf file under the property yarn.resourcemanager.webapp.address
  - resourcemanager_uri: http://localhost:8088

init_config:
 general_counters:
 - counter_group_name: 'org.apache.hadoop.mapreduce.TaskCounter'
   counters:
   - counter_name: 'MAP_INPUT_RECORDS'
   - counter_name: 'MAP_OUTPUT_RECORDS'
   - counter_name: 'REDUCE_INPUT_RECORDS'
   - counter_name: 'REDUCE_OUTPUT_RECORDS'
# Add more counters
# - counter_group_name: 'org.apache.hadoop.mapreduce.FileSystemCounter'
#   counters:
#     - counter_name: 'HDFS_BYTES_READ'
# etc
```

Restart the Agent to begin sending Mapreduce metrics to Datadog.

# Validation

Run the Agent's `info` subcommand and look for `mapreduce` under the Checks section:

```
  Checks
  ======
    [...]

    mapreduce
    -------
      - instance #0 [OK]
      - Collected 36 metrics, 0 events & 1 service check

    [...]
```

# Compatibility

The mapreduce check is compatible with all major platforms.

# Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/mapreduce/metadata.csv) for a list of metrics provided by this check.

The metrics available are collected using df from Spotify’s Snakebite. hdfs.in_use is calculated by dividing used by capacity.

# Service Checks

`mapreduce.resource_manager.can_connect`:

Returns CRITICAL if the Agent cannot connect to the ResourceManager to collect metrics, otherwise OK.

`mapreduce.application_master.can_connect`:

Returns CRITICAL if the Agent cannot connect to the Application Master to collect metrics, otherwise OK.

# Further Reading

To get a better idea of how (or why) to collect Mapreduce (and other Hadoop) metrics, check out our [series of blog posts](https://www.datadoghq.com/blog/hadoop-architecture-overview/) about it.
