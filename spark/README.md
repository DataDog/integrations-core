# Spark Check
{{< img src="integrations/spark/sparkgraph.png" alt="spark graph" responsive="true" popup="true">}}
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


If you need the newest version of the Spark check, install the `dd-check-spark` package; this package's check overrides the one packaged with the Agent. See the [integrations-core repository README.md for more details](https://docs.datadoghq.com/agent/faq/install-core-extra/).

### Configuration

Create a file `spark.yaml` in the Agent's `conf.d` directory. See the [sample spark.yaml](https://github.com/DataDog/integrations-core/blob/master/spark/conf.yaml.example) for all available configuration options:

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

[Restart the Agent](https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent) to start sending Spark metrics to Datadog.

### Validation

[Run the Agent's `status` subcommand](https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information) and look for `spark` under the Checks section:

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
- **spark.application_master.can_connect**
- **spark.resource_manager.can_connect**

The checks return CRITICAL if the Agent cannot collect Spark metrics, otherwise OK.

## Troubleshooting
### Spark on AWS EMR.

To get Spark metrics if Spark is set up on AWS EMR, [use bootstrap actions](https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-plan-bootstrap.html) to install the [Datadog Agent](https://docs.datadoghq.com/agent/) and then create the `/etc/dd-agent/conf.d/spark.yaml` configuration file with [the proper values on each EMR node](https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-connect-master-node-ssh.html).

## Further Reading

* [Hadoop & Spark monitoring with Datadog](https://www.datadoghq.com/blog/monitoring-spark/)
