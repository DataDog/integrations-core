# Agent Check: Databricks

## Overview

Monitor your [Databricks][1] clusters with the Datadog [Spark integration][6].

## Setup

### Installation

Monitor Databricks Spark applications with the [Datadog Spark integration][2]. Install the Datadog Agent on your clusters following the [Configuration](#configuration) instructions for your appropriate cluster.

### Configuration

Configure the Spark integration to monitor your Apache Spark Cluster on Databricks and collect system and Spark metrics.

Be sure to replace the `<DATADOG_API_KEY>` placeholders with your own API key and run the notebook once to save the init script as a global configuration. Read more about the Databricks Datadog Init scripts [here][2].

When configuring the cluster, add `DD_ENVIRONMENT` environment variable to add a global environment tag.

#### Standard cluster

<!-- xxx tabs xxx -->
<!-- xxx tab "Driver only" xxx -->
##### Install the Datadog Agent on Driver
Create a notebook with the following script to install the Datadog Agent on the driver node of the cluster.
to install the Datadog Agent and collect system and Spark metrics.

This is a updated version of the [Datadog Init Script][4] Databricks notebook

```shell script
%python 

dbutils.fs.put("dbfs:/<init-script-folder>/datadog-install-driver-only.sh","""
#!/bin/bash

echo "Running on the driver? $DB_IS_DRIVER"
echo "Driver ip: $DB_DRIVER_IP"

cat <<EOF >> /tmp/start_datadog.sh
#!/bin/bash

if [[ \${DB_IS_DRIVER} = "TRUE" ]]; then
  echo "On the driver. Installing Datadog ..."
  
  # INSTALL THE LATEST DATADOG AGENT 7
  DD_AGENT_MAJOR_VERSION=7 DD_API_KEY=<DATADOG_API_KEY> bash -c "\$(curl -L https://raw.githubusercontent.com/DataDog/datadog-agent/master/cmd/agent/install_script.sh)"
  
  # WAITING UNTIL MASTER PARAMS ARE LOADED, THEN GRABBING IP AND PORT
  while [ -z \$gotparams ]; do
    if [ -e "/tmp/master-params" ]; then
      DB_DRIVER_PORT=\$(cat /tmp/master-params | cut -d' ' -f2)
      gotparams=TRUE
    fi
    sleep 2
  done

  sudo sed -i 's/^# env: <environment name>\$/env: ${DD_ENV}/g' /etc/datadog-agent/datadog.yaml
  ddline=\$(sudo sed -n  '\|^# tags:\$|=' /etc/datadog-agent/datadog.yaml)
  ddnum=\$((ddline + 3))
  hostip=\$(hostname -I | xargs)  
  
  # WRITING CONFIG FILE FOR SPARK INTEGRATION WITH STRUCTURED STREAMING METRICS ENABLED
  # MODIFY TO INCLUDE OTHER OPTIONS IN spark.d/conf.yaml.example
  echo "init_config:
instances:
    - spark_url: http://\$DB_DRIVER_IP:\$DB_DRIVER_PORT
      spark_cluster_mode: spark_standalone_mode
      cluster_name: \${hostip}
      streaming_metrics: true" > /etc/datadog-agent/conf.d/spark.yaml

  # INCLUDE GLOBAL TAGS (environment, cluster_id, cluster_name)
  sudo sed -i '/# tags:/ s/^/tags:\\n  - environment:${DD_ENVIRONMENT}\\n  - host_ip:${SPARK_LOCAL_IP}\\n  - spark_host:driver\\n/'  /etc/datadog-agent/datadog.yaml

  # RESTARTING AGENT
  sudo service datadog-agent restart

fi
EOF

# CLEANING UP
if [ \$DB_IS_DRIVER ]; then
  chmod a+x /tmp/start_datadog.sh
  /tmp/start_datadog.sh >> /tmp/datadog_start.log 2>&1 & disown
fi
""", True)
```

<!-- xxz tab xxx -->
<!-- xxx tab "All nodes" xxx -->
##### Install the Datadog Agent on Driver and Worker Nodes

```shell script
%python 

dbutils.fs.put("dbfs:/tmp/datadog-install-driver-workers.sh","""
#!/bin/bash
cat <<EOF >> /tmp/start_datadog.sh

#!/bin/bash
  

  # INSTALL THE LATEST DATADOG AGENT 7 ON DRIVER AND WORKER NODES
  DD_AGENT_MAJOR_VERSION=7 DD_API_KEY=<DATADOG_API_KEY> bash -c "\$(curl -L https://s3.amazonaws.com/dd-agent/scripts/install_script.sh)"
  
  sudo sed -i 's/^# env: <environment name>\$/env: ${DD_ENV}/g' /etc/datadog-agent/datadog.yaml
  ddline=\$(sudo sed -n  '\|^# tags:\$|=' /etc/datadog-agent/datadog.yaml)
  ddnum=\$((ddline + 3))

  hostip=$(hostname -I | xargs)

if [[ \${DB_IS_DRIVER} = "TRUE" ]]; then

  echo "Installing Datadog agent in the driver (master node) ..."

  # WRITING CONFIG FILE FOR SPARK INTEGRATION WITH STRUCTURED STREAMING METRICS ENABLED
  # MODIFY TO INCLUDE OTHER OPTIONS IN spark.d/conf.yaml.example
  echo "init_config:
instances:
    - spark_url: http://\${DB_DRIVER_IP}:\${SPARK_UI_PORT}
      spark_cluster_mode: spark_driver_mode
      cluster_name: \${hostip}
      streaming_metrics: true" > /etc/datadog-agent/conf.d/spark.d/conf.yaml

  # INCLUDE GLOBAL TAGS (environment, cluster_id, cluster_name)
  sudo sed -i '/# tags:/ s/^/tags:\\n  - environment:${DD_ENVIRONMENT}\\n  - host_ip:${SPARK_LOCAL_IP}\\n  - spark_host:driver\\n/'  /etc/datadog-agent/datadog.yaml
else
  sudo sed -i '/# tags:/ s/^/tags:\\n  - environment:${DD_ENVIRONMENT}\\n   - host_ip:${SPARK_LOCAL_IP}\\n  - spark_host:worker\\n/'  /etc/datadog-agent/datadog.yaml
fi

  # RESTARTING AGENT
  sudo service datadog-agent restart
EOF

# CLEANING UP
chmod a+x /tmp/start_datadog.sh
/tmp/start_datadog.sh >> /tmp/datadog_start.log 2>&1 & disown
""", True)
```
<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

#### Job cluster

For job clusters, use the following script to configure the Spark integration.

**Note**: Job clusters are monitored in `spark_driver_mode` with the Spark UI port.


```shell script
#!/bin/bash

echo "Running on the driver? $DB_IS_DRIVER"
echo "Driver ip: $DB_DRIVER_IP"

cat <<EOF >> /tmp/start_datadog.sh
#!/bin/bash

if [ \$DB_IS_DRIVER ]; then
  echo "On the driver. Installing Datadog ..."

  # INSTALL THE LATEST DATADOG AGENT 7
  DD_AGENT_MAJOR_VERSION=7 DD_API_KEY=<DATADOG_API_KEY> bash -c "\$(curl -L https://s3.amazonaws.com/dd-agent/scripts/install_script.sh)"

  while [ -z \$gotparams ]; do
    if [ -e "/tmp/driver-env.sh" ]; then
      DB_DRIVER_PORT=\$(grep -i "CONF_UI_PORT" /tmp/driver-env.sh | cut -d'=' -f2)
      gotparams=TRUE
    fi
    sleep 2
  done

  current=\$(hostname -I | xargs)

  # WRITING SPARK CONFIG FILE
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

See the [Spark integration documentation][7] for a list of metrics collected.


### Service Checks

See the [Spark integration documentation][8] for the list of service checks collected.
 
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
[7]: https://docs.datadoghq.com/integrations/spark/#metrics
[8]: https://docs.datadoghq.com/integrations/spark/#service-checks
