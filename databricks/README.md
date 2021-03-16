# Agent Check: Databricks

## Overview

Monitor your [Databricks][1] clusters with the Datadog [Spark integration][6].

## Setup

### Installation

Monitor Databricks Spark applications with the [Datadog Spark integration][2]. Install the Datadog Agent on your clusters following the [Configuration](#configuration) instructions for your appropriate cluster.

### Configuration

Configure the Spark integration to monitor your Apache Spark Cluster on Databricks and collect system and Spark metrics.

1. Determine the best init script below for your Databricks cluster environment. 

2. Copy and run the contents into a notebook. The notebook will create an init script that will install a Datadog Agent on your clusters.
    The notebook only needs to be run once to save the script as a global configuration. Read more about the Databricks Datadog Init scripts [here][2].
    - Set `<init-script-folder>` path to where you want your init scripts to be saved in.
        
3. Configure a new Databricks cluster with the cluster-scoped init script path using the UI, Databricks CLI, or invoking the Clusters API.
    - Set the `DD_API_KEY` environment variable in the cluster's Advanced Options with your Datadog API key.
    - Add `DD_ENV` environment variable under Advanced Options to add a global environment tag to better identify your clusters.


#### Standard cluster

<!-- xxx tabs xxx -->
<!-- xxx tab "Driver only" xxx -->
##### Install the Datadog Agent on Driver
Install the Datadog Agent on the driver node of the cluster. This is a updated version of the [Datadog Init Script][4] Databricks notebook example.

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
  
  # CONFIGURE HOST TAGS FOR CLUSTER
  DD_TAGS="environment:\${DD_ENV}","databricks_cluster_id:\${DB_CLUSTER_ID}","databricks_cluster_name:\${DB_CLUSTER_NAME}","spark_host_ip:${SPARK_LOCAL_IP}","spark_node:driver"

  # INSTALL THE LATEST DATADOG AGENT 7
  DD_AGENT_MAJOR_VERSION=7 DD_API_KEY=\$DD_API_KEY DD_HOST_TAGS=DD_TAGS bash -c "\$(curl -L https://raw.githubusercontent.com/DataDog/datadog-agent/master/cmd/agent/install_script.sh)"

  # WAIT FOR DATADOG AGENT TO BE INSTALLED
  while [ -z \$datadoginstalled ]; do
    if [ -e "/etc/datadog-agent/datadog.yaml" ]; then
      datadoginstalled=TRUE
    fi
    sleep 2
  done

  echo "Datadog Agent is installed"

  # ENABLE LOGS IN datadog.yaml TO COLLECT DRIVER LOGS
  echo "logs_enabled: true" >> /etc/datadog-agent/datadog.yaml

  # WAITING UNTIL MASTER PARAMS ARE LOADED, THEN GRABBING IP AND PORT
  while [ -z \$gotparams ]; do
    if [ -e "/tmp/master-params" ]; then
      DB_DRIVER_PORT=\$(cat /tmp/master-params | cut -d' ' -f2)
      gotparams=TRUE
    fi
    sleep 2
  done

  hostip=\$(hostname -I | xargs)  

  # WRITING CONFIG FILE FOR SPARK INTEGRATION WITH STRUCTURED STREAMING METRICS ENABLED AND LOGS CONFIGURATION
  # MODIFY TO INCLUDE OTHER OPTIONS IN spark.d/conf.yaml.example
  echo "init_config:
instances:
    - spark_url: http://\$DB_DRIVER_IP:\$DB_DRIVER_PORT
      spark_cluster_mode: spark_standalone_mode
      cluster_name: \${hostip}
      streaming_metrics: true
logs:
    - type: file
      path: /databricks/driver/logs/*.log
      source: databricks
      service: databricks
      log_processing_rules:
        - type: multi_line
          name: new_log_start_with_date
          pattern: \d{2,4}[\-\/]\d{2,4}[\-\/]\d{2,4}.*" > /etc/datadog-agent/conf.d/spark.yaml

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

dbutils.fs.put("dbfs:/<init-script-folder>/datadog-install-driver-workers.sh","""
#!/bin/bash
cat <<EOF >> /tmp/start_datadog.sh

#!/bin/bash
  
  hostip=$(hostname -I | xargs)

if [[ \${DB_IS_DRIVER} = "TRUE" ]]; then

  echo "Installing Datadog agent in the driver (master node) ..."
  # CONFIGURE HOST TAGS FOR DRIVER
  DD_TAGS="environment:\${DD_ENV}","databricks_cluster_id:\${DB_CLUSTER_ID}","databricks_cluster_name:\${DB_CLUSTER_NAME}","spark_host_ip:${SPARK_LOCAL_IP}","spark_node:driver"

  # INSTALL THE LATEST DATADOG AGENT 7 ON DRIVER AND WORKER NODES
  DD_AGENT_MAJOR_VERSION=7 DD_API_KEY=\$DD_API_KEY DD_HOST_TAGS=\$DD_TAGS bash -c "\$(curl -L https://s3.amazonaws.com/dd-agent/scripts/install_script.sh)"
  
  # WAIT FOR DATADOG AGENT TO BE INSTALLED
  while [ -z \$datadoginstalled ]; do
    if [ -e "/etc/datadog-agent/datadog.yaml" ]; then
      datadoginstalled=TRUE
    fi
    sleep 2
  done
  echo "Datadog Agent is installed"

  # ENABLE LOGS IN datadog.yaml TO COLLECT DRIVER LOGS
  echo "logs_enabled: true" >> /etc/datadog-agent/datadog.yaml

  while [ -z \$gotparams ]; do
    if [ -e "/tmp/driver-env.sh" ]; then
      DB_DRIVER_PORT=\$(grep -i "CONF_UI_PORT" /tmp/driver-env.sh | cut -d'=' -f2)
      gotparams=TRUE
    fi
    sleep 2
  done

  # WRITING CONFIG FILE FOR SPARK INTEGRATION WITH STRUCTURED STREAMING METRICS ENABLED
  # MODIFY TO INCLUDE OTHER OPTIONS IN spark.d/conf.yaml.example
  echo "init_config:
instances:
    - spark_url: http://\${DB_DRIVER_IP}:\${DB_DRIVER_PORT}
      spark_cluster_mode: spark_driver_mode
      cluster_name: \${hostip}
      streaming_metrics: true
logs:
    - type: file
      path: /databricks/driver/logs/*.log
      source: databricks
      service: databricks
      log_processing_rules:
        - type: multi_line
          name: new_log_start_with_date
          pattern: \d{2,4}[\-\/]\d{2,4}[\-\/]\d{2,4}.*" > /etc/datadog-agent/conf.d/spark.yaml
else

  # CONFIGURE HOST TAGS FOR WORKERS
  DD_TAGS="environment:\${DD_ENV}","databricks_cluster_id:\${DB_CLUSTER_ID}","databricks_cluster_name:\${DB_CLUSTER_NAME}","spark_host_ip:${SPARK_LOCAL_IP}","spark_node:worker"

  # INSTALL THE LATEST DATADOG AGENT 7 ON DRIVER AND WORKER NODES
  DD_AGENT_MAJOR_VERSION=7 DD_API_KEY=\$DD_API_KEY DD_HOST_TAGS=\$DD_TAGS bash -c "\$(curl -L https://s3.amazonaws.com/dd-agent/scripts/install_script.sh)"

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
%python 

dbutils.fs.put("dbfs:/<init-script-folder>/datadog-install-job-driver-mode.sh","""
#!/bin/bash

echo "Running on the driver? $DB_IS_DRIVER"
echo "Driver ip: $DB_DRIVER_IP"

cat <<EOF >> /tmp/start_datadog.sh
#!/bin/bash

if [ \$DB_IS_DRIVER ]; then
  echo "On the driver. Installing Datadog ..."

  # CONFIGURE HOST TAGS FOR DRIVER
  DD_TAGS="environment:\${DD_ENV}","databricks_cluster_id:\${DB_CLUSTER_ID}","databricks_cluster_name:\${DB_CLUSTER_NAME}","spark_host_ip:${SPARK_LOCAL_IP}","spark_node:driver"

  # INSTALL THE LATEST DATADOG AGENT 7 ON DRIVER AND WORKER NODES
  DD_AGENT_MAJOR_VERSION=7 DD_API_KEY=\$DD_API_KEY DD_HOST_TAGS=\$DD_TAGS bash -c "\$(curl -L https://s3.amazonaws.com/dd-agent/scripts/install_script.sh)"

  # WAIT FOR DATADOG AGENT TO BE INSTALLED
  while [ -z \$datadoginstalled ]; do
    if [ -e "/etc/datadog-agent/datadog.yaml" ]; then
      datadoginstalled=TRUE
    fi
    sleep 2
  done
  echo "Datadog Agent is installed"  

  # ENABLE LOGS IN datadog.yaml TO COLLECT DRIVER LOGS
  echo "logs_enabled: true" >> /etc/datadog-agent/datadog.yaml

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
      cluster_name: \$current
logs:
    - type: file
      path: /databricks/driver/logs/*.log
      source: databricks
      service: databricks
      log_processing_rules:
        - type: multi_line
          name: new_log_start_with_date
          pattern: \d{2,4}[\-\/]\d{2,4}[\-\/]\d{2,4}.*" > /etc/datadog-agent/conf.d/spark.yaml

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
