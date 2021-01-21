# Agent Check: Databricks

## Overview

This check monitors [Databricks][1].

## Setup

### Installation

The Databricks check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

Use the [Spark Integration][2] to monitor your Apache Spark Cluster.

#### Standard cluster

Use the [Datadog Init Script][4] Databricks notebook to install the Datadog Agent and collect system and Spark metrics.

```yaml
init_config:
instances:
    - spark_url: http://\$DB_DRIVER_IP:\$DB_DRIVER_PORT
      spark_cluster_mode: spark_standalone_mode
      cluster_name: \$current" > /etc/datadog-agent/conf.d/spark.yaml
```

#### Job cluster

Modify the Spark integration configuration in the [Datadog Init Script][4] to monitor job clusters:

```yaml
init_config:
instances:
    - spark_url: http://\$DB_DRIVER_IP:\$SPARK_UI_PORT
      spark_cluster_mode: spark_driver_mode
      cluster_name: \$current" > /etc/datadog-agent/conf.d/spark.yaml
```

**Note**: The Spark UI port is dynamically set unless you configure the `spark.ui.port` in the `Spark Config` of the cluster configuration page.
Create the environment variable `SPARK_UI_PORT` with the same value to use the init script.

### Validation

[Run the Agent's status subcommand][5] and look for `spark` under the Checks section.

## Data Collected

### Metrics

Databricks does not include any metrics.

### Service Checks

Databricks does not include any service checks.

### Events

Databricks does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][3].

[1]: https://databricks.com/
[2]: https://databricks.com/blog/2017/06/01/apache-spark-cluster-monitoring-with-databricks-and-datadog.html
[3]: https://docs.datadoghq.com/help/
[4]: https://docs.databricks.com/_static/notebooks/datadog-init-script.html
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/?#agent-status-and-information
