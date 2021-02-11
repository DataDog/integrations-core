# Agent Check: Databricks

## Overview

Monitor your [Databricks][1] clusters with the Datadog [Spark integration][6].

## Setup

### Installation

Monitor Databricks Spark applications with the [Datadog Spark integration][2]. No additional installation is needed on your server.

### Configuration

Configure the [Spark integration][2] to monitor your Apache Spark Cluster.

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

For job clusters, use the following script to configure the Spark integration.

    Note: Job clusters are monitored in `spark_driver_mode` via the Spark UI port.


```shell script
#!/bin/bash

echo "Running on the driver? $DB_IS_DRIVER"
echo "Driver ip: $DB_DRIVER_IP"

cat <<EOF >> /tmp/start_datadog.sh
#!/bin/bash

if [ \$DB_IS_DRIVER ]; then
  echo "On the driver. Installing Datadog ..."

  # install the Datadog agent
  DD_API_KEY=<API_KEY> bash -c "\$(curl -L https://raw.githubusercontent.com/DataDog/datadog-agent/master/cmd/agent/install_script.sh)"

  while [ -z \$gotparams ]; do
    if [ -e "/tmp/driver-env.sh" ]; then
      DB_DRIVER_PORT=\$(grep -i "CONF_UI_PORT" /tmp/driver-env.sh | cut -d'=' -f2)
      gotparams=TRUE
    fi
    sleep 2
  done

  current=\$(hostname -I | xargs)

  # WRITING SPARK CONFIG FILE FOR STREAMING SPARK METRICS
  echo "init_config:
instances:
    - spark_url: http://\$DB_DRIVER_IP:\$DB_DRIVER_PORT
      spark_cluster_mode: spark_driver_mode
      cluster_name: \$current" > /etc/datadog-agent/conf.d/spark.yaml

  # RESTARTING AGENT
  sudo service datadog-agent restart

fi
EOF

# CLEANING UP
if [ \$DB_IS_DRIVER ]; then
  chmod a+x /tmp/start_datadog.sh
  /tmp/start_datadog.sh >> /tmp/datadog_start.log 2>&1 & disown
fi

```


### Validation

[Run the Agent's status subcommand][5] and look for `spark` under the Checks section.

## Data Collected

### Metrics

The Databricks integration does not include any metrics.

### Service Checks

The Databricks integration does not include any service checks.

### Events

The Databricks integration does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][3].

[1]: https://databricks.com/
[2]: https://databricks.com/blog/2017/06/01/apache-spark-cluster-monitoring-with-databricks-and-datadog.html
[3]: https://docs.datadoghq.com/help/
[4]: https://docs.databricks.com/_static/notebooks/datadog-init-script.html
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/?#agent-status-and-information
[6]: https://docs.datadoghq.com/integrations/spark/?tab=host