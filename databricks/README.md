# Agent Check: Databricks

## Overview

Monitor your [Databricks][1] clusters with the Datadog [Spark integration][2].

## Setup

### Installation

Monitor Databricks Spark applications with the [Datadog Spark integration][3]. Install the [Datadog Agent][4] on your clusters following the [Configuration](#configuration) instructions for your appropriate cluster.

### Configuration

Configure the Spark integration to monitor your Apache Spark Cluster on Databricks and collect system and Spark metrics.

1. Determine the best init script below for your Databricks cluster environment. 

2. Copy and run the contents into a notebook. The notebook creates an init script that installs a Datadog Agent on your clusters.
    The notebook only needs to be run once to save the script as a global configuration. 
    - Set `<init-script-folder>` path to where you want your init scripts to be saved in.
        
3. Configure a new Databricks cluster with the cluster-scoped init script path using the UI, Databricks CLI, or invoking the Clusters API.
    - Set the `DD_API_KEY` environment variable in the cluster's Advanced Options with your Datadog API key.
    - Add `DD_ENV` environment variable under Advanced Options to add a global environment tag to better identify your clusters.
    - Set `DD_SITE` to your [site URL][11].


#### Standard cluster

<!-- xxx tabs xxx -->
<!-- xxx tab "Driver only" xxx -->
##### Install the Datadog Agent on Driver
Install the Datadog Agent on the driver node of the cluster. 

After creating the `datadog-install-driver-only.sh` script, add the init script path in the [cluster configuration page][6].

```shell script
%python 

dbutils.fs.put("dbfs:/<init-script-folder>/datadog-install-driver-only.sh","""
#!/bin/bash

date -u +"%Y-%m-%d %H:%M:%S UTC"
echo "Running on the driver? $DB_IS_DRIVER"
echo "Driver ip: $DB_DRIVER_IP"

cat <<EOF > /tmp/start_datadog.sh
#!/bin/bash

if [[ \${DB_IS_DRIVER} = "TRUE" ]]; then
  
  echo "Installing Datadog Agent on the driver..."
  
  # CONFIGURE HOST TAGS FOR CLUSTER
  DD_TAGS="environment:\${DD_ENV}","databricks_cluster_id:\${DB_CLUSTER_ID}","databricks_cluster_name:\${DB_CLUSTER_NAME}","spark_host_ip:\${SPARK_LOCAL_IP}","spark_node:driver"

  # INSTALL THE LATEST DATADOG AGENT 7
  DD_INSTALL_ONLY=true DD_API_KEY=\$DD_API_KEY DD_HOST_TAGS=\$DD_TAGS bash -c "\$(curl -L https://s3.amazonaws.com/dd-agent/scripts/install_script_agent7.sh)"

  # WAIT FOR DATADOG AGENT TO BE INSTALLED
  while [ -z \$datadoginstalled ]; do
    if [ -e "/etc/datadog-agent/datadog.yaml" ]; then
      datadoginstalled=TRUE
    fi
    sleep 2
  done

  echo "Datadog Agent is installed"

  # ENABLE LOGS IN datadog.yaml TO COLLECT DRIVER LOGS
  sed -i '/.*logs_enabled:.*/a logs_enabled: true' /etc/datadog-agent/datadog.yaml

  # CONFIGURE HOSTNAME EXPLICITLY IN datadog.yaml TO PREVENT AGENT FROM FAILING ON VERSION 7.40+
  # SEE https://github.com/DataDog/datadog-agent/issues/14152 FOR CHANGE
  hostname=\$(hostname | xargs)
  echo "hostname: \$hostname" >> /etc/datadog-agent/datadog.yaml

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
      source: spark
      service: databricks
      log_processing_rules:
        - type: multi_line
          name: new_log_start_with_date
          pattern: \d{2,4}[\-\/]\d{2,4}[\-\/]\d{2,4}.*" > /etc/datadog-agent/conf.d/spark.d/spark.yaml

  # RESTARTING AGENT
  sleep 15
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
##### Install the Datadog Agent on driver and worker nodes

After creating the `datadog-install-driver-workers.sh` script, add the init script path in the [cluster configuration page][6].

```shell script
%python 

dbutils.fs.put("dbfs:/<init-script-folder>/datadog-install-driver-workers.sh","""
#!/bin/bash
cat <<EOF > /tmp/start_datadog.sh

#!/bin/bash

date -u +"%Y-%m-%d %H:%M:%S UTC"
echo "Running on the driver? $DB_IS_DRIVER"
echo "Driver ip: $DB_DRIVER_IP"

if [[ \${DB_IS_DRIVER} = "TRUE" ]]; then

  echo "Installing Datadog Agent on the driver (master node)."
  
  # CONFIGURE HOST TAGS FOR DRIVER
  DD_TAGS="environment:\${DD_ENV}","databricks_cluster_id:\${DB_CLUSTER_ID}","databricks_cluster_name:\${DB_CLUSTER_NAME}","spark_host_ip:\${SPARK_LOCAL_IP}","spark_node:driver"

  # INSTALL THE LATEST DATADOG AGENT 7 ON DRIVER AND WORKER NODES
  DD_INSTALL_ONLY=true DD_API_KEY=\$DD_API_KEY DD_HOST_TAGS=\$DD_TAGS bash -c "\$(curl -L https://s3.amazonaws.com/dd-agent/scripts/install_script_agent7.sh)"
  
  # WAIT FOR DATADOG AGENT TO BE INSTALLED
  while [ -z \$datadoginstalled ]; do
    if [ -e "/etc/datadog-agent/datadog.yaml" ]; then
      datadoginstalled=TRUE
    fi
    sleep 2
  done

  echo "Datadog Agent is installed"

  # ENABLE LOGS IN datadog.yaml TO COLLECT DRIVER LOGS
  sed -i '/.*logs_enabled:.*/a logs_enabled: true' /etc/datadog-agent/datadog.yaml

  # CONFIGURE HOSTNAME EXPLICITLY IN datadog.yaml TO PREVENT AGENT FROM FAILING ON VERSION 7.40+
  # SEE https://github.com/DataDog/datadog-agent/issues/14152 FOR CHANGE
  hostname=\$(hostname | xargs)
  echo "hostname: \$hostname" >> /etc/datadog-agent/datadog.yaml

  while [ -z \$gotparams ]; do
    if [ -e "/tmp/driver-env.sh" ]; then
      DB_DRIVER_PORT=\$(grep -i "CONF_UI_PORT" /tmp/driver-env.sh | cut -d'=' -f2)
      gotparams=TRUE
    fi
    sleep 2
  done

  hostip=$(hostname -I | xargs)

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
      source: spark
      service: databricks
      log_processing_rules:
        - type: multi_line
          name: new_log_start_with_date
          pattern: \d{2,4}[\-\/]\d{2,4}[\-\/]\d{2,4}.*" > /etc/datadog-agent/conf.d/spark.d/spark.yaml
else

  # CONFIGURE HOST TAGS FOR WORKERS
  DD_TAGS="environment:\${DD_ENV}","databricks_cluster_id:\${DB_CLUSTER_ID}","databricks_cluster_name:\${DB_CLUSTER_NAME}","spark_host_ip:\${SPARK_LOCAL_IP}","spark_node:worker"

  # INSTALL THE LATEST DATADOG AGENT 7 ON DRIVER AND WORKER NODES
  DD_INSTALL_ONLY=true DD_API_KEY=\$DD_API_KEY DD_HOST_TAGS=\$DD_TAGS bash -c "\$(curl -L https://s3.amazonaws.com/dd-agent/scripts/install_script_agent7.sh)"

fi

  # RESTARTING AGENT
  sleep 15
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
After creating the `datadog-install-job-driver-mode.sh` script, add the init script path in the [cluster configuration page][6].

**Note**: Job clusters are monitored in `spark_driver_mode` with the Spark UI port.


```shell script
%python 

dbutils.fs.put("dbfs:/<init-script-folder>/datadog-install-job-driver-mode.sh","""
#!/bin/bash

date -u +"%Y-%m-%d %H:%M:%S UTC"
echo "Running on the driver? $DB_IS_DRIVER"
echo "Driver ip: $DB_DRIVER_IP"

cat <<EOF >> /tmp/start_datadog.sh
#!/bin/bash

if [ \$DB_IS_DRIVER ]; then

  echo "Installing Datadog Agent on the driver..."

  # CONFIGURE HOST TAGS FOR DRIVER
  DD_TAGS="environment:\${DD_ENV}","databricks_cluster_id:\${DB_CLUSTER_ID}","databricks_cluster_name:\${DB_CLUSTER_NAME}","spark_host_ip:\${SPARK_LOCAL_IP}","spark_node:driver"

  # INSTALL THE LATEST DATADOG AGENT 7 ON DRIVER AND WORKER NODES
  DD_INSTALL_ONLY=true DD_API_KEY=\$DD_API_KEY DD_HOST_TAGS=\$DD_TAGS bash -c "\$(curl -L https://s3.amazonaws.com/dd-agent/scripts/install_script_agent7.sh)"

  # WAIT FOR DATADOG AGENT TO BE INSTALLED
  while [ -z \$datadoginstalled ]; do
    if [ -e "/etc/datadog-agent/datadog.yaml" ]; then
      datadoginstalled=TRUE
    fi
    sleep 2
  done

  echo "Datadog Agent is installed"  

  # ENABLE LOGS IN datadog.yaml TO COLLECT DRIVER LOGS
  sed -i '/.*logs_enabled:.*/a logs_enabled: true' /etc/datadog-agent/datadog.yaml

  # CONFIGURE HOSTNAME EXPLICITLY IN datadog.yaml TO PREVENT AGENT FROM FAILING ON VERSION 7.40+
  # SEE https://github.com/DataDog/datadog-agent/issues/14152 FOR CHANGE
  hostname=\$(hostname | xargs)
  echo "hostname: \$hostname" >> /etc/datadog-agent/datadog.yaml

  while [ -z \$gotparams ]; do
    if [ -e "/tmp/driver-env.sh" ]; then
      DB_DRIVER_PORT=\$(grep -i "CONF_UI_PORT" /tmp/driver-env.sh | cut -d'=' -f2)
      gotparams=TRUE
    fi
    sleep 2
  done

  hostip=\$(hostname -I | xargs)

  # WRITING SPARK CONFIG FILE
  echo "init_config:
instances:
    - spark_url: http://\$DB_DRIVER_IP:\$DB_DRIVER_PORT
      spark_cluster_mode: spark_driver_mode
      cluster_name: \$hostip
logs:
    - type: file
      path: /databricks/driver/logs/*.log
      source: spark
      service: databricks
      log_processing_rules:
        - type: multi_line
          name: new_log_start_with_date
          pattern: \d{2,4}[\-\/]\d{2,4}[\-\/]\d{2,4}.*" > /etc/datadog-agent/conf.d/spark.d/spark.yaml

  # RESTARTING AGENT
  sleep 15
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

[Run the Agent's status subcommand][7] and look for `spark` under the Checks section.

## Data Collected

### Metrics

See the [Spark integration documentation][8] for a list of metrics collected.

### Service Checks

See the [Spark integration documentation][9] for the list of service checks collected.
 
### Events

The Databricks integration does not include any events.

## Troubleshooting

### Failed to bind port 6062

[`ipywidgets`][14] are available in Databricks Runtime 11.0 and above. By default, `ipywidgets` occupies port `6062`, 
which is also the default Datadog Agent port for [the debug endpoint][13]. Because of that, you can run into this issue:

```
23/02/28 17:07:31 ERROR DriverDaemon$: XXX Fatal uncaught exception. Terminating driver.
java.io.IOException: Failed to bind to 0.0.0.0/0.0.0.0:6062
```

To fix this issue, you have several options: 

1. With Databricks Runtime 11.2 and above, you can change the port using the Spark `spark.databricks.driver.ipykernel.commChannelPort` option. Find more information in [the Databricks documentation][12].
2. You can configure the port used by the Datadog Agent with the `process_config.expvar_port` in your [`datadog.yaml`][13] configuration file. 
3. Alternatively, you can set the `DD_PROCESS_CONFIG_EXPVAR_PORT` environment variable to configure the port used by the Datadog agent.

Need help? Contact [Datadog support][10].

## Further Reading

{{< partial name="whats-next/whats-next.html" >}}

[1]: https://databricks.com/
[2]: https://docs.datadoghq.com/integrations/spark/?tab=host
[3]: https://app.datadoghq.com/integrations/spark
[4]: https://app.datadoghq.com/account/settings#agent
[6]: https://docs.databricks.com/clusters/init-scripts.html#configure-a-cluster-scoped-init-script-using-the-ui
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/?#agent-status-and-information
[8]: https://docs.datadoghq.com/integrations/spark/#metrics
[9]: https://docs.datadoghq.com/integrations/spark/#service-checks
[10]: https://docs.datadoghq.com/help/
[11]: https://docs.datadoghq.com/getting_started/site/
[12]: https://docs.databricks.com/notebooks/ipywidgets.html#requirements
[13]: https://github.com/DataDog/datadog-agent/blob/7.43.x/pkg/config/config_template.yaml#L1262-L1266
[14]: https://docs.databricks.com/notebooks/ipywidgets.html