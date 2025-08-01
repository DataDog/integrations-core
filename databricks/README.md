# Agent Check: Databricks

<div class="alert alert-info">
<a href="https://docs.datadoghq.com/data_jobs/">Data Jobs Monitoring</a> helps you observe, troubleshoot, and cost-optimize your Databricks jobs and clusters.<br/><br/>
This page is limited to documentation for ingesting Databricks model serving metrics, cluster utilization data, and reference tables.
</div>

![Databricks default dashboard][21]

## Overview

Datadog offers several Databricks monitoring capabilities.

[Data Jobs Monitoring][25] provides monitoring for your Databricks jobs and clusters. You can detect problematic Databricks jobs and workflows anywhere in your data pipelines, remediate failed and long-running-jobs faster, and optimize cluster resources to reduce costs.

[Cloud Cost Management][26] gives you a view to analyze all your Databricks DBU costs alongside the associated cloud spend.

[Log Management][27] enables you to aggregate and analyze logs from your Databricks jobs & clusters. You can collect these logs as part of [Data Jobs Monitoring][25].

[Infrastructure Monitoring][28] gives you a limited subset of the Data Jobs Monitoring functionality - visibility into the resource utilization of your Databricks clusters and Apache Spark performance metrics.

[Reference Tables][32] allow you to import metadata from your Databricks workspace into Datadog. These tables enrich your Datadog telemetry with critical context like workspace names, job definitions, cluster configurations, and user roles.

Model serving metrics provide insights into how your  Databricks model serving infrastructure is performing. With these metrics, you can detect endpoints that have high error rate, high latency, are over/under provisioned, and more.
## Setup

### Installation
Gain insight into the health of your model serving infrastructure by following the [Model Serving Configuration](#model-serving-configuration) instructions.

Monitor Databricks Spark applications with the [Datadog Spark integration][3]. Install the [Datadog Agent][4] on your clusters following the [configuration](#spark-configuration) instructions for your appropriate cluster. Refer to [Spark Configuration](#spark-configuration) instructions.

### Configuration
#### Model Serving Configuration
<!-- xxx tabs xxx -->

<!-- xxx tab "Use a Service Principal for OAuth" xxx -->
<div class="alert alert-warning">New workspaces must authenticate using OAuth. Workspaces integrated with a Personal Access Token continue to function and can switch to OAuth at any time. After a workspace starts using OAuth, it cannot revert to a Personal Access Token.</div>

1. In your Databricks account, click on **User Management** in the left menu. Then, under the **Service principals** tab, click **Add service principal**.
2. Under the **Credentials & secrets** tab, click **Generate secret**. Set **Lifetime (days)** to the maximum value allowed (730), then click **Generate**. Take note of your client ID and client secret. Also take note of your account ID, which can be found by clicking on your profile in the upper-right corner.
3. Click **Workspaces** in the left menu, then select the name of your workspace.
4. Go to the **Permissions** tab and click **Add permissions**.
5. Search for the service principal you created and assign it the **Admin** permission.
6. In Datadog, open the Databricks integration tile.
7. On the **Configure** tab, click **Add Databricks Workspace**.
9. Enter a workspace name, your Databricks workspace URL, account ID, and the client ID and secret you generated.
10. In the **Select resources to set up collection** section, make sure **Metrics - Model Serving** is **Enabled**.
<!-- xxz tab xxx -->

<!-- xxx tab "Use a Personal Access Token (Legacy)" xxx -->
<div class="alert alert-warning">This option is only available for workspaces created before July 7, 2025. New workspaces must authenticate using OAuth.</div>

1. In your Databricks workspace, click on your profile in the top right corner and go to **Settings**. Select **Developer** in the left side bar. Next to **Access tokens**, click **Manage**.
2. Click **Generate new token**, enter "Datadog Integration" in the **Comment** field, remove the default value in **Lifetime (days)**, and click **Generate**. Take note of your token.

   **Important:**
   * Make sure you delete the default value in **Lifetime (days)** so that the token doesn't expire and the integration doesn't break.
   * Ensure the account generating the token has [CAN VIEW access][30] for the Databricks jobs and clusters you want to monitor.

   As an alternative, follow the [official Databricks documentation][31] to generate an access token for a [service principal][31].

3. In Datadog, open the Databricks integration tile.
4. On the **Configure** tab, click **Add Databricks Workspace**.
5. Enter a workspace name, your Databricks workspace URL, and the Databricks token you generated.
6. In the **Select resources to set up collection** section, make sure **Metrics - Model Serving** is **Enabled**.
<!-- xxz tab xxx -->

<!-- xxz tabs xxx -->

#### Reference Table Configuration
1. Configure a workspace in Datadog's Databricks integration tile.
2. In the accounts detail panel, click **Reference Tables**.
3. In the **Reference Tables** tab, click **Add New Reference Table**.
4. Provide the **Reference table name**, **Databricks table name**, and **Primary key** of your Databricks view or table.

  * For optimal results, create a view in Databricks that includes only the specific data you want to send to Datadog. This means generating a dedicated table that reflects the exact scope needed for your use case.

5. Click **Save**.

#### Spark Configuration
Configure the Spark integration to monitor your Apache Spark Cluster on Databricks and collect system and Spark metrics.

Each script described below can be modified to suits your needs. For instance, you can:
- Add specific tags to your instances.
- Modify the Spark integration configuration.

<!-- partial
{{% site-region region="us,us3,us5,eu,gov,ap1" %}}
You can also define or modify environment variables with the cluster-scoped init script path using the UI, Databricks CLI, or invoking the Clusters API:
  - Set `DD_API_KEY` to better identify your clusters.
  - Set `DD_ENV` to better identify your clusters.
  - Set `DD_SITE` to your site: {{< region-param key="dd_site" code="true" >}}. Defaults to `datadoghq.com`
{{% /site-region %}}
partial -->

<div class="alert alert-warning">For security reasons, it's not recommended to define the `DD_API_KEY` environment variable in plain text directly in the UI. Instead, use <a href="https://docs.databricks.com/en/security/secrets/index.html">Databricks secrets</a>.</div>



#### With a global init script

A global init script runs on every cluster created in your workspace. Global init scripts are useful when you want to enforce organization-wide library configurations or security screens. 

<div class="alert alert-info">Only workspace admins can manage global init scripts.</div>
<div class="alert alert-info">Global init scripts only run on clusters configured with single user or legacy no-isolation shared access mode. Therefore, Databricks recommends configuring all init scripts as cluster-scoped and managing them across your workspace using cluster policies.</div>

Use the Databricks UI to edit the global init scripts:

1. Choose one of the following scripts to install the Agent on the driver or on the driver and worker nodes of the cluster.
2. Modify the script to suit your needs. For example, you can add tags or define a specific configuration for the integration.
3. Go to the Admin Settings and click the **Global Init Scripts** tab.
4. Click on the **+ Add** button.
5. Name the script, for example `Datadog init script` and then paste it in the **Script** field.
6. Click on the **Enabled** toggle to enable it.
7. Click on the **Add** button.

After these steps, any new cluster uses the script automatically. More information on global init scripts can be found in the [Databricks official documentation][16].

<div class="alert alert-info">You can define several init scripts and specify their order in the UI.</div>

<!-- xxx tabs xxx -->
<!-- xxx tab "Driver only" xxx -->
##### Install the Datadog Agent on driver

Install the Datadog Agent on the driver node of the cluster. 

<div class="alert alert-warning">You need to define the value of the `DD_API_KEY` variable inside the script.</div>

```shell script
#!/bin/bash
cat <<EOF > /tmp/start_datadog.sh
#!/bin/bash

date -u +"%Y-%m-%d %H:%M:%S UTC"
echo "Running on the driver? \$DB_IS_DRIVER"
echo "Driver ip: \$DB_DRIVER_IP"

DB_CLUSTER_NAME=$(echo "$DB_CLUSTER_NAME" | sed -e 's/ /_/g' -e "s/'/_/g")
DD_API_KEY='<YOUR_API_KEY>'

if [[ \${DB_IS_DRIVER} = "TRUE" ]]; then
  echo "Installing Datadog Agent on the driver..."

  # CONFIGURE HOST TAGS FOR DRIVER
  DD_TAGS="environment:\${DD_ENV}","databricks_cluster_id:\${DB_CLUSTER_ID}","databricks_cluster_name:\${DB_CLUSTER_NAME}","spark_host_ip:\${DB_DRIVER_IP}","spark_node:driver","databricks_instance_type:\${DB_INSTANCE_TYPE}","databricks_is_job_cluster:\${DB_IS_JOB_CLUSTER}"

  # INSTALL THE LATEST DATADOG AGENT 7 ON DRIVER AND WORKER NODES
  DD_INSTALL_ONLY=true \
    DD_API_KEY=\$DD_API_KEY \
    DD_HOST_TAGS=\$DD_TAGS \
    DD_HOSTNAME="\$(hostname | xargs)" \
    DD_SITE="\${DD_SITE:-datadoghq.com}" \
    bash -c "\$(curl -L https://s3.amazonaws.com/dd-agent/scripts/install_script_agent7.sh)"

  # Avoid conflicts on port 6062
  echo "process_config.expvar_port: 6063" >> /etc/datadog-agent/datadog.yaml

  echo "Datadog Agent is installed"

  while [ -z \$DB_DRIVER_PORT ]; do
    if [ -e "/tmp/driver-env.sh" ]; then
      DB_DRIVER_PORT="\$(grep -i "CONF_UI_PORT" /tmp/driver-env.sh | cut -d'=' -f2)"
    fi
    echo "Waiting 2 seconds for DB_DRIVER_PORT"
    sleep 2
  done

  echo "DB_DRIVER_PORT=\$DB_DRIVER_PORT"

  # WRITING CONFIG FILE FOR SPARK INTEGRATION WITH STRUCTURED STREAMING METRICS ENABLED
  # MODIFY TO INCLUDE OTHER OPTIONS IN spark.d/conf.yaml.example
  echo "init_config:
instances:
    - spark_url: http://\${DB_DRIVER_IP}:\${DB_DRIVER_PORT}
      spark_cluster_mode: spark_driver_mode
      cluster_name: \${DB_CLUSTER_NAME}
      streaming_metrics: true
      executor_level_metrics: true
logs:
    - type: file
      path: /databricks/driver/logs/*.log
      source: spark
      service: databricks
      log_processing_rules:
        - type: multi_line
          name: new_log_start_with_date
          pattern: \d{2,4}[\-\/]\d{2,4}[\-\/]\d{2,4}.*" > /etc/datadog-agent/conf.d/spark.d/spark.yaml

  echo "Spark integration configured"

  # ENABLE LOGS IN datadog.yaml TO COLLECT DRIVER LOGS
  sed -i '/.*logs_enabled:.*/a logs_enabled: true' /etc/datadog-agent/datadog.yaml
fi

echo "Restart the agent"
sudo service datadog-agent restart
EOF

chmod a+x /tmp/start_datadog.sh
/tmp/start_datadog.sh >> /tmp/datadog_start.log 2>&1 & disown
```

<!-- xxz tab xxx -->
<!-- xxx tab "All nodes" xxx -->
##### Install the Datadog Agent on driver and worker nodes

Install the Datadog Agent on the driver and worker nodes of the cluster.

<div class="alert alert-warning">You will need to define the value of the `DD_API_KEY` variable inside the script.</div>

```shell script
#!/bin/bash
cat <<EOF > /tmp/start_datadog.sh
#!/bin/bash

date -u +"%Y-%m-%d %H:%M:%S UTC"
echo "Running on the driver? \$DB_IS_DRIVER"
echo "Driver ip: \$DB_DRIVER_IP"

DB_CLUSTER_NAME=$(echo "$DB_CLUSTER_NAME" | sed -e 's/ /_/g' -e "s/'/_/g")
DD_API_KEY='<YOUR_API_KEY>'

if [[ \${DB_IS_DRIVER} = "TRUE" ]]; then
  echo "Installing Datadog Agent on the driver (master node)."

  # CONFIGURE HOST TAGS FOR DRIVER
  DD_TAGS="environment:\${DD_ENV}","databricks_cluster_id:\${DB_CLUSTER_ID}","databricks_cluster_name:\${DB_CLUSTER_NAME}","spark_host_ip:\${DB_DRIVER_IP}","spark_node:driver","databricks_instance_type:\${DB_INSTANCE_TYPE}","databricks_is_job_cluster:\${DB_IS_JOB_CLUSTER}"

  # INSTALL THE LATEST DATADOG AGENT 7 ON DRIVER AND WORKER NODES
  DD_INSTALL_ONLY=true \
    DD_API_KEY=\$DD_API_KEY \
    DD_HOST_TAGS=\$DD_TAGS \
    DD_HOSTNAME="\$(hostname | xargs)" \
    DD_SITE="\${DD_SITE:-datadoghq.com}" \
    bash -c "\$(curl -L https://s3.amazonaws.com/dd-agent/scripts/install_script_agent7.sh)"

  echo "Datadog Agent is installed"

  while [ -z \$DB_DRIVER_PORT ]; do
    if [ -e "/tmp/driver-env.sh" ]; then
      DB_DRIVER_PORT="\$(grep -i "CONF_UI_PORT" /tmp/driver-env.sh | cut -d'=' -f2)"
    fi
    echo "Waiting 2 seconds for DB_DRIVER_PORT"
    sleep 2
  done

  echo "DB_DRIVER_PORT=\$DB_DRIVER_PORT"

  # WRITING CONFIG FILE FOR SPARK INTEGRATION WITH STRUCTURED STREAMING METRICS ENABLED
  # MODIFY TO INCLUDE OTHER OPTIONS IN spark.d/conf.yaml.example
  echo "init_config:
instances:
    - spark_url: http://\${DB_DRIVER_IP}:\${DB_DRIVER_PORT}
      spark_cluster_mode: spark_driver_mode
      cluster_name: \${DB_CLUSTER_NAME}
      streaming_metrics: true
      executor_level_metrics: true
logs:
    - type: file
      path: /databricks/driver/logs/*.log
      source: spark
      service: databricks
      log_processing_rules:
        - type: multi_line
          name: new_log_start_with_date
          pattern: \d{2,4}[\-\/]\d{2,4}[\-\/]\d{2,4}.*" > /etc/datadog-agent/conf.d/spark.d/spark.yaml

  echo "Spark integration configured"

  # ENABLE LOGS IN datadog.yaml TO COLLECT DRIVER LOGS
  sed -i '/.*logs_enabled:.*/a logs_enabled: true' /etc/datadog-agent/datadog.yaml
else
  echo "Installing Datadog Agent on the worker."

  # CONFIGURE HOST TAGS FOR WORKERS
  DD_TAGS="environment:\${DD_ENV}","databricks_cluster_id:\${DB_CLUSTER_ID}","databricks_cluster_name:\${DB_CLUSTER_NAME}","spark_host_ip:\${SPARK_LOCAL_IP}","spark_node:worker","databricks_instance_type:\${DB_INSTANCE_TYPE}","databricks_is_job_cluster:\${DB_IS_JOB_CLUSTER}"

  # INSTALL THE LATEST DATADOG AGENT 7 ON DRIVER AND WORKER NODES
  # CONFIGURE HOSTNAME EXPLICITLY IN datadog.yaml TO PREVENT AGENT FROM FAILING ON VERSION 7.40+
  # SEE https://github.com/DataDog/datadog-agent/issues/14152 FOR CHANGE
  DD_INSTALL_ONLY=true DD_API_KEY=\$DD_API_KEY DD_HOST_TAGS=\$DD_TAGS DD_HOSTNAME="\$(hostname | xargs)" bash -c "\$(curl -L https://s3.amazonaws.com/dd-agent/scripts/install_script_agent7.sh)"

  echo "Datadog Agent is installed"
fi

# Avoid conflicts on port 6062
echo "process_config.expvar_port: 6063" >> /etc/datadog-agent/datadog.yaml

echo "Restart the agent"
sudo service datadog-agent restart
EOF

chmod a+x /tmp/start_datadog.sh
/tmp/start_datadog.sh >> /tmp/datadog_start.log 2>&1 & disown

```

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

#### With a cluster-scoped init script 

Cluster-scoped init scripts are init scripts defined in a cluster configuration. Cluster-scoped init scripts apply to both clusters you create and those created to run jobs. Databricks supports configuration and storage of init scripts through:
- Workspace Files
- Unity Catalog Volumes
- Cloud Object Storage

Use the Databricks UI to edit the cluster to run the init script:

1. Choose one of the following scripts to install the Agent on the driver or on the driver and worker nodes of the cluster.
2. Modify the script to suit your needs. For example, you can add tags or define a specific configuration for the integration.
3. Save the script into your workspace with the **Workspace** menu on the left. If using **Unity Catalog Volume**, save the script in your **Volume** with the **Catalog** menu on the left.
4. On the cluster configuration page, click the **Advanced** options toggle.
5. In the **Environment variables**, specify the `DD_API_KEY` environment variable and, optionally, the `DD_ENV` and the `DD_SITE` environment variables.
6. Go to the **Init Scripts** tab.
7. In the **Destination** dropdown, select the `Workspace` destination type. If using **Unity Catalog Volume**, in the **Destination** dropdown, select the `Volume` destination type.
8. Specify a path to the init script. 
9. Click on the **Add** button.

If you stored your `datadog_init_script.sh` directly in the `Shared` workspace, you can access the file at the following path: `/Shared/datadog_init_script.sh`.

If you stored your `datadog_init_script.sh` directly in a user workspace, you can access the file at the following path: `/Users/$EMAIL_ADDRESS/datadog_init_script.sh`.

If you stored your `datadog_init_script.sh` directly in a `Unity Catalog Volume`, you can access the file at the following path: `/Volumes/$VOLUME_PATH/datadog_init_script.sh`.

More information on cluster init scripts can be found in the [Databricks official documentation][16].

<!-- xxx tabs xxx -->
<!-- xxx tab "Driver only" xxx -->
##### Install the Datadog Agent on Driver

Install the Datadog Agent on the driver node of the cluster. 

```shell script
#!/bin/bash
cat <<EOF > /tmp/start_datadog.sh
#!/bin/bash

date -u +"%Y-%m-%d %H:%M:%S UTC"
echo "Running on the driver? \$DB_IS_DRIVER"
echo "Driver ip: \$DB_DRIVER_IP"

DB_CLUSTER_NAME=$(echo "$DB_CLUSTER_NAME" | sed -e 's/ /_/g' -e "s/'/_/g")

if [[ \${DB_IS_DRIVER} = "TRUE" ]]; then
  echo "Installing Datadog Agent on the driver..."

  # CONFIGURE HOST TAGS FOR DRIVER
  DD_TAGS="environment:\${DD_ENV}","databricks_cluster_id:\${DB_CLUSTER_ID}","databricks_cluster_name:\${DB_CLUSTER_NAME}","spark_host_ip:\${DB_DRIVER_IP}","spark_node:driver","databricks_instance_type:\${DB_INSTANCE_TYPE}","databricks_is_job_cluster:\${DB_IS_JOB_CLUSTER}"

  # INSTALL THE LATEST DATADOG AGENT 7 ON DRIVER AND WORKER NODES
  DD_INSTALL_ONLY=true \
    DD_API_KEY=\$DD_API_KEY \
    DD_HOST_TAGS=\$DD_TAGS \
    DD_HOSTNAME="\$(hostname | xargs)" \
    DD_SITE="\${DD_SITE:-datadoghq.com}" \
    bash -c "\$(curl -L https://s3.amazonaws.com/dd-agent/scripts/install_script_agent7.sh)"

  # Avoid conflicts on port 6062
  echo "process_config.expvar_port: 6063" >> /etc/datadog-agent/datadog.yaml

  echo "Datadog Agent is installed"

  while [ -z \$DB_DRIVER_PORT ]; do
    if [ -e "/tmp/driver-env.sh" ]; then
      DB_DRIVER_PORT="\$(grep -i "CONF_UI_PORT" /tmp/driver-env.sh | cut -d'=' -f2)"
    fi
    echo "Waiting 2 seconds for DB_DRIVER_PORT"
    sleep 2
  done

  echo "DB_DRIVER_PORT=\$DB_DRIVER_PORT"

  # WRITING CONFIG FILE FOR SPARK INTEGRATION WITH STRUCTURED STREAMING METRICS ENABLED
  # MODIFY TO INCLUDE OTHER OPTIONS IN spark.d/conf.yaml.example
  echo "init_config:
instances:
    - spark_url: http://\${DB_DRIVER_IP}:\${DB_DRIVER_PORT}
      spark_cluster_mode: spark_driver_mode
      cluster_name: \${DB_CLUSTER_NAME}
      streaming_metrics: true
      executor_level_metrics: true
logs:
    - type: file
      path: /databricks/driver/logs/*.log
      source: spark
      service: databricks
      log_processing_rules:
        - type: multi_line
          name: new_log_start_with_date
          pattern: \d{2,4}[\-\/]\d{2,4}[\-\/]\d{2,4}.*" > /etc/datadog-agent/conf.d/spark.d/spark.yaml

  echo "Spark integration configured"

  # ENABLE LOGS IN datadog.yaml TO COLLECT DRIVER LOGS
  sed -i '/.*logs_enabled:.*/a logs_enabled: true' /etc/datadog-agent/datadog.yaml
fi


echo "Restart the agent"
sudo service datadog-agent restart
EOF

chmod a+x /tmp/start_datadog.sh
/tmp/start_datadog.sh >> /tmp/datadog_start.log 2>&1 & disown
```

<!-- xxz tab xxx -->
<!-- xxx tab "All nodes" xxx -->
##### Install the Datadog Agent on driver and worker nodes

Install the Datadog Agent on the driver and worker nodes of the cluster.

```shell script
#!/bin/bash
cat <<EOF > /tmp/start_datadog.sh
#!/bin/bash

date -u +"%Y-%m-%d %H:%M:%S UTC"
echo "Running on the driver? \$DB_IS_DRIVER"
echo "Driver ip: \$DB_DRIVER_IP"

DB_CLUSTER_NAME=$(echo "$DB_CLUSTER_NAME" | sed -e 's/ /_/g' -e "s/'/_/g")

if [[ \${DB_IS_DRIVER} = "TRUE" ]]; then
  echo "Installing Datadog Agent on the driver (master node)."

  # CONFIGURE HOST TAGS FOR DRIVER
  DD_TAGS="environment:\${DD_ENV}","databricks_cluster_id:\${DB_CLUSTER_ID}","databricks_cluster_name:\${DB_CLUSTER_NAME}","spark_host_ip:\${DB_DRIVER_IP}","spark_node:driver","databricks_instance_type:\${DB_INSTANCE_TYPE}","databricks_is_job_cluster:\${DB_IS_JOB_CLUSTER}"

  # INSTALL THE LATEST DATADOG AGENT 7 ON DRIVER AND WORKER NODES
  DD_INSTALL_ONLY=true \
    DD_API_KEY=\$DD_API_KEY \
    DD_HOST_TAGS=\$DD_TAGS \
    DD_HOSTNAME="\$(hostname | xargs)" \
    DD_SITE="\${DD_SITE:-datadoghq.com}" \
    bash -c "\$(curl -L https://s3.amazonaws.com/dd-agent/scripts/install_script_agent7.sh)"

  echo "Datadog Agent is installed"

  while [ -z \$DB_DRIVER_PORT ]; do
    if [ -e "/tmp/driver-env.sh" ]; then
      DB_DRIVER_PORT="\$(grep -i "CONF_UI_PORT" /tmp/driver-env.sh | cut -d'=' -f2)"
    fi
    echo "Waiting 2 seconds for DB_DRIVER_PORT"
    sleep 2
  done

  echo "DB_DRIVER_PORT=\$DB_DRIVER_PORT"

  # WRITING CONFIG FILE FOR SPARK INTEGRATION WITH STRUCTURED STREAMING METRICS ENABLED
  # MODIFY TO INCLUDE OTHER OPTIONS IN spark.d/conf.yaml.example
  echo "init_config:
instances:
    - spark_url: http://\${DB_DRIVER_IP}:\${DB_DRIVER_PORT}
      spark_cluster_mode: spark_driver_mode
      cluster_name: \${DB_CLUSTER_NAME}
      streaming_metrics: true
      executor_level_metrics: true
logs:
    - type: file
      path: /databricks/driver/logs/*.log
      source: spark
      service: databricks
      log_processing_rules:
        - type: multi_line
          name: new_log_start_with_date
          pattern: \d{2,4}[\-\/]\d{2,4}[\-\/]\d{2,4}.*" > /etc/datadog-agent/conf.d/spark.d/spark.yaml

  echo "Spark integration configured"

  # ENABLE LOGS IN datadog.yaml TO COLLECT DRIVER LOGS
  sed -i '/.*logs_enabled:.*/a logs_enabled: true' /etc/datadog-agent/datadog.yaml
else
  echo "Installing Datadog Agent on the worker."

  # CONFIGURE HOST TAGS FOR WORKERS
  DD_TAGS="environment:\${DD_ENV}","databricks_cluster_id:\${DB_CLUSTER_ID}","databricks_cluster_name:\${DB_CLUSTER_NAME}","spark_host_ip:\${SPARK_LOCAL_IP}","spark_node:worker","databricks_instance_type:\${DB_INSTANCE_TYPE}","databricks_is_job_cluster:\${DB_IS_JOB_CLUSTER}"

  # INSTALL THE LATEST DATADOG AGENT 7 ON DRIVER AND WORKER NODES
  # CONFIGURE HOSTNAME EXPLICITLY IN datadog.yaml TO PREVENT AGENT FROM FAILING ON VERSION 7.40+
  # SEE https://github.com/DataDog/datadog-agent/issues/14152 FOR CHANGE
  DD_INSTALL_ONLY=true DD_API_KEY=\$DD_API_KEY DD_HOST_TAGS=\$DD_TAGS DD_HOSTNAME="\$(hostname | xargs)" bash -c "\$(curl -L https://s3.amazonaws.com/dd-agent/scripts/install_script_agent7.sh)"

  echo "Datadog Agent is installed"
fi

# Avoid conflicts on port 6062
echo "process_config.expvar_port: 6063" >> /etc/datadog-agent/datadog.yaml

echo "Restart the agent"
sudo service datadog-agent restart
EOF

chmod a+x /tmp/start_datadog.sh
/tmp/start_datadog.sh >> /tmp/datadog_start.log 2>&1 & disown
```

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

## Data Collected

### Metrics
#### Model Serving Metrics
See [metadata.csv][29] for a list of metrics provided by this integration.
#### Spark Metrics
See the [Spark integration documentation][8] for a list of Spark metrics collected.

### Service Checks

See the [Spark integration documentation][9] for the list of service checks collected.
 
### Events

The Databricks integration does not include any events.

## Troubleshooting

You can troubleshoot issues yourself by enabling the [Databricks web terminal][18] or by using a [Databricks Notebook][19]. Consult the [Agent Troubleshooting][20] documentation for information on useful troubleshooting steps. 

Need help? Contact [Datadog support][10].

## Further Reading

Additional helpful documentation, links, and articles:

- [Uploading a Script to Unity Catalog Volume][24]

[1]: https://databricks.com/
[2]: https://docs.datadoghq.com/integrations/spark/?tab=host
[3]: /integrations/spark
[4]: /account/settings/agent/latest
[6]: https://docs.databricks.com/clusters/init-scripts.html#configure-a-cluster-scoped-init-script-using-the-ui
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/?#agent-status-and-information
[8]: https://docs.datadoghq.com/integrations/spark/#metrics
[9]: https://docs.datadoghq.com/integrations/spark/#service-checks
[10]: https://docs.datadoghq.com/help/
[12]: https://docs.databricks.com/notebooks/ipywidgets.html#requirements
[13]: https://github.com/DataDog/datadog-agent/blob/7.43.x/pkg/config/config_template.yaml#L1262-L1266
[14]: https://docs.databricks.com/notebooks/ipywidgets.html
[15]: https://docs.datadoghq.com/getting_started/site/
[16]: https://docs.databricks.com/clusters/init-scripts.html#global-init-scripts
[17]: https://docs.databricks.com/clusters/init-scripts.html#cluster-scoped-init-scripts
[18]: https://docs.databricks.com/en/clusters/web-terminal.html
[19]: https://docs.databricks.com/en/notebooks/index.html
[20]: https://docs.datadoghq.com/agent/troubleshooting/
[21]: https://raw.githubusercontent.com/DataDog/integrations-core/master/databricks/images/databricks_dashboard.png
[22]: https://www.datadoghq.com/blog/databricks-monitoring-datadog/
[23]: /integrations/spark
[24]: https://docs.databricks.com/en/ingestion/add-data/upload-to-volume.html#upload-files-to-a-unity-catalog-volume
[25]: https://www.datadoghq.com/product/data-jobs-monitoring/
[26]: https://www.datadoghq.com/product/cloud-cost-management/
[27]: https://www.datadoghq.com/product/log-management/
[28]: https://docs.datadoghq.com/integrations/databricks/?tab=driveronly
[29]: https://github.com/DataDog/integrations-core/blob/master/databricks/metadata.csv
[30]: https://docs.databricks.com/en/security/auth-authz/access-control/index.html#job-acls
[31]: https://docs.databricks.com/en/admin/users-groups/service-principals.html#what-is-a-service-principal
[32]: https://docs.datadoghq.com/reference_tables
