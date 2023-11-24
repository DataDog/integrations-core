# Spark Check

![Spark Graph][1]

## Overview

This check monitors [Spark][2] through the Datadog Agent. Collect Spark metrics for:

- Drivers and executors: RDD blocks, memory used, disk used, duration, etc.
- RDDs: partition count, memory used, and disk used.
- Tasks: number of tasks active, skipped, failed, and total.
- Job state: number of jobs active, completed, skipped, and failed.

## Setup

### Installation

The Spark check is included in the [Datadog Agent][3] package. No additional installation is needed on your Mesos master (for Spark on Mesos), YARN ResourceManager (for Spark on YARN), or Spark master (for Spark Standalone).

### Configuration

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

1. Edit the `spark.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][4]. The following parameters may require updating. See the [sample spark.d/conf.yaml][5] for all available configuration options.

   ```yaml
   init_config:

   instances:
     - spark_url: http://localhost:8080 # Spark master web UI
       #   spark_url: http://<Mesos_master>:5050 # Mesos master web UI
       #   spark_url: http://<YARN_ResourceManager_address>:8088 # YARN ResourceManager address

       spark_cluster_mode: spark_yarn_mode # default
       #   spark_cluster_mode: spark_mesos_mode
       #   spark_cluster_mode: spark_yarn_mode
       #   spark_cluster_mode: spark_driver_mode

       # required; adds a tag 'cluster_name:<CLUSTER_NAME>' to all metrics
       cluster_name: "<CLUSTER_NAME>"
       # spark_pre_20_mode: true   # if you use Standalone Spark < v2.0
       # spark_proxy_enabled: true # if you have enabled the spark UI proxy
   ```

2. [Restart the Agent][6].

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][7] for guidance on applying the parameters below.

| Parameter            | Value                                                             |
| -------------------- | ----------------------------------------------------------------- |
| `<INTEGRATION_NAME>` | `spark`                                                           |
| `<INIT_CONFIG>`      | blank or `{}`                                                     |
| `<INSTANCE_CONFIG>`  | `{"spark_url": "%%host%%:8080", "cluster_name":"<CLUSTER_NAME>"}` |

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Log collection

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

      ```yaml
       logs_enabled: true
     ```

2. Uncomment and edit the logs configuration block in your `spark.d/conf.yaml` file. Change the `type`, `path`, and `service` parameter values based on your environment. See the [sample spark.d/conf.yaml][5] for all available configuration options.

      ```yaml
       logs:
         - type: file
           path: <LOG_FILE_PATH>
           source: spark
           service: <SERVICE_NAME>
           # To handle multi line that starts with yyyy-mm-dd use the following pattern
           # log_processing_rules:
           #   - type: multi_line
           #     pattern: \d{4}\-(0?[1-9]|1[012])\-(0?[1-9]|[12][0-9]|3[01])
           #     name: new_log_start_with_date
     ```

3. [Restart the Agent][6].

To enable logs for Docker environments, see [Docker Log Collection][8].

### Validation

Run the Agent's [status subcommand][9] and look for `spark` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][10] for a list of metrics provided by this check.

### Events

The Spark check does not include any events.

### Service Checks

See [service_checks.json][11] for a list of service checks provided by this integration.

## Troubleshooting

### Spark on AWS EMR

To receive metrics for Spark on AWS EMR, [use bootstrap actions][12] to install the [Datadog Agent][13]:

For Agent v5, create the `/etc/dd-agent/conf.d/spark.yaml` configuration file with the [proper values on each EMR node][14].

For Agent v6/7, create the `/etc/datadog-agent/conf.d/spark.d/conf.yaml` configuration file with the [proper values on each EMR node][14].

### Successful check but no metrics are collected

The Spark integration only collects metrics about running apps. If you have no currently running apps, the check will just submit a health check.

## Further Reading

Additional helpful documentation, links, and articles:

- [Hadoop and Spark monitoring with Datadog][15]
- [Monitoring Apache Spark applications running on Amazon EMR][16]

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/spark/images/sparkgraph.png
[2]: https://spark.apache.org/
[3]: https://app.datadoghq.com/account/settings/agent/latest
[4]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[5]: https://github.com/DataDog/integrations-core/blob/master/spark/datadog_checks/spark/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[7]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[8]: https://docs.datadoghq.com/agent/docker/log/
[9]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[10]: https://github.com/DataDog/integrations-core/blob/master/spark/metadata.csv
[11]: https://github.com/DataDog/integrations-core/blob/master/spark/assets/service_checks.json
[12]: https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-plan-bootstrap.html
[13]: https://docs.datadoghq.com/agent/
[14]: https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-connect-master-node-ssh.html
[15]: https://www.datadoghq.com/blog/monitoring-spark
[16]: https://www.datadoghq.com/blog/spark-emr-monitoring/ 
