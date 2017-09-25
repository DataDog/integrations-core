# Spark Check

## Overview

The Spark check collects metrics for:

- Drivers and executors: RDD blocks, memory used, disk used, duration, etc.
- RDDs: partition count, memory used, disk used
- Tasks: number of tasks active, skipped, failed, total
- Job state: number of jobs active, completed, skipped, failed

## Setup
### Installation

The Spark check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your:

- Mesos master (if you're running Spark on Mesos),
- YARN ResourceManager (if you're running Spark on YARN), or
- Spark master (if you're running Standalone Spark)

If you need the newest version of the check, install the `dd-check-spark` package.

### Configuration

Create a file `spark.yaml` in the Agent's `conf.d` directory:

```
init_config:

instances:
  - spark_url: http://localhost:8088 # Spark master web UI 
#   spark_url: http://<Mesos_master>:5050 # Mesos master web UI
#   spark_url: http://<YARN_ResourceManager_address>:8088 # YARN ResourceManager address

    spark_cluster_mode: spark_standalone_mode # default is spark_yarn_mode
#   spark_cluster_mode: spark_mesos_mode
#   spark_cluster_mode: spark_yarn_mode

    cluster_name: <CLUSTER_NAME> # required; adds a tag 'cluster_name:<CLUSTER_NAME>' to all metrics

#   spark_pre_20_mode: true   # if you use Standalone Spark < v2.0
#   spark_proxy_enabled: true # if you have enabled the spark UI proxy
```

Set `spark_url` and `spark_cluster_mode` according to how you're running Spark.

Restart the Agent to start sending Spark metrics to Datadog.

### Validation

Run the Agent's `info` subcommand and look for `spark` under the Checks section:

```
  Checks
  ======
    [...]

    spark
    -------
      - instance #0 [OK]
      - Collected 26 metrics, 0 events & 1 service check

    [...]
```

## Compatibility

The spark check is compatible with all major platforms.

## Data Collected
### Metrics
See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/spark/metadata.csv) for a list of metrics provided by this check.

### Events
The Spark check does not include any event at this time.

### Service Checks
The Agent submits one of the following service checks, depending on how you're running Spark:

- **spark.standalone_master.can_connect**
- **spark.mesos_master.can_connect**
- **spark.resource_manager.can_connect**

The checks return CRITICAL if the Agent cannot collect Spark metrics, otherwise OK.

## Troubleshooting

If you have any questions about Datadog or a use case our [Docs](https://docs.datadoghq.com/) didn’t mention, we’d love to help! Here’s how you can reach out to us:

### Visit the Knowledge Base

Learn more about what you can do in Datadog on the [Support Knowledge Base](https://datadog.zendesk.com/agent/).

### Web Support

Messages in the [event stream](https://app.datadoghq.com/event/stream) containing **@support-datadog** will reach our Support Team. This is a convenient channel for referencing graph snapshots or a particular event. In addition, we have a livechat service available during the day (EST) from any page within the app.

### By Email

You can also contact our Support Team via email at [support@datadoghq.com](mailto:support@datadoghq.com).

### Over Slack

Reach out to our team and other Datadog users on [Slack](http://chat.datadoghq.com/).

## Further Reading
To get a better idea of how (or why) to monitor Hadoop & Spark with Datadog, check out our [series of blog posts](https://www.datadoghq.com/blog/monitoring-spark/) about it.
