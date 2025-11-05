# Falco Integration for Datadog

## Overview

[Falco][1] is a cloud-native security tool. It provides near real-time threat detection for cloud, container, and Kubernetes workloads by leveraging runtime insights. Falco can monitor events defined with customizable rules from various sources, including the Linux kernel, and enrich them with metadata from the Kubernetes API server, container runtime, and more.
This integration ingests the following logs:

- Alert: Represents details such as the rule name, description, condition, output message, priority level, and tags

The Falco integration seamlessly ingests the data of Falco logs using the webhook. Before ingestion of the data, it normalizes and enriches the logs, ensuring a consistent data format and enhancing information content for downstream processing and analysis. The integration provides insights into alert logs through the out-of-the-box dashboards.

**Minimum Agent version:** 7.59.1

## Setup

### Configuration

#### Metric collection

Falco exposes Prometheus-formatted metrics that provide observability into its runtime, event processing, and security posture. The Datadog Agent can collect these metrics using the OpenMetrics integration. Follow the steps below to enable and configure metric collection from Falco.

##### 1. Enable Prometheus Metrics in Falco

Edit your `falco.yaml` configuration file to enable the metrics endpoint:

```yaml
metrics:
  enabled: true
  listen_address: "<FALCO_HOST>"
  listen_port: 8765
```

Restart Falco to apply the changes:

```bash
systemctl restart falco
```

If Falco is installed using Helm, you can enable metrics with:

```bash
helm upgrade -i falco falcosecurity/falco \
  --set metrics.enabled=true \
  --set metrics.listen_address="<FALCO_HOST>" \
  --set metrics.listen_port=8765
```

##### 2. Configure the Datadog Agent

Update your Datadog Agent configuration to scrape Falco's Prometheus metrics endpoint. For example, add the following to `conf.d/prometheus.d/conf.yaml`:

```yaml
instances:
  - openmetrics_endpoint: http://<FALCO_HOST>:8765/metrics
```

Replace `<FALCO_HOST>` with the hostname or IP address where Falco is running.

For Kubernetes environments, you can use [Autodiscovery Integration Templates][6] to configure the Agent to automatically discover and scrape Falco metrics endpoints.

##### 3. Validation

After configuration, verify that Falco metrics are being ingested by Datadog. You should see metrics with the prefix `falco.` in the Datadog Metrics Explorer.

#### Log Collection

<!-- xxx tabs xxx -->
<!-- xxx tab "API Forwarding" xxx -->
##### API Forwarding
- Update the settings in the configuration file (`falco.yaml`) as shown below:

  ```yaml
  json_output: true
  http_output:
    enabled: true
    url: <DATADOG_WEBHOOK_URL> 
  ```
  
  **Note:** Replace `<DATADOG_WEBHOOK_URL>` with the correct intake URL for your [Datadog site][7], such as `https://http-intake.logs.us3.datadoghq.com/api/v2/logs?dd-api-key=<dd-api-key>&ddsource=falco` for US3. 

  - Restart the Falco using below command:

    ```bash
    systemctl restart falco
    ```

- If Falco is installed using Helm, you can use the following command to add or update the HTTP URL:

  ```bash
  helm upgrade -i falco falcosecurity/falco \
  --set falco.http_output.enabled=true \
  --set falco.http_output.url="<DATADOG_WEBHOOK_URL>" \
  --set falco.json_output=true \
  --set json_include_output_property=true
  ```

  **Note:** Replace `<DATADOG_WEBHOOK_URL>` with the correct intake URL for your [Datadog site][7], such as `https://http-intake.logs.us3.datadoghq.com/api/v2/logs?dd-api-key=<dd-api-key>&ddsource=falco` for US3. 

<!-- xxz tab xxx -->
<!-- xxx tab "Agent" xxx -->
##### Agent
Update the settings in the configuration file (`falco.yaml`) as shown below:

  ```yaml
  json_output: true
  file_output:
    enabled: true
    filename: <PATH TO LOGS>
  ```

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

2. Add this configuration block to your `falco.d/conf.yaml` file to start collecting your Falco Logs:

   ```yaml
   logs:
     - type: file
       path: <PATH TO LOGS>
       service: <SERVICE NAME>
       source: falco
   ```

    Change the `path` and `service` parameter values and configure them for your environment. See the [sample falco.d/conf.yaml][4] for all available configuration options.

3. [Restart the Agent][5].

**Note**: Ensure the `datadog-agent` user has read and execute access to tail the log files you want to collect from.
<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->
>>>>>>> master

## Data Collected

### Metrics

See [metadata.csv][3] for a list of metrics provided by this integration.

### Logs

The Falco integration collects and forwards Falco alert logs to Datadog.

### Events

The Falco integration does not include any events.

## Support

For further assistance, contact [Datadog Support][2].

[1]: https://falco.org/docs/getting-started/
[2]: https://docs.datadoghq.com/help/
[3]: https://github.com/DataDog/integrations-core/blob/master/falco/metadata.csv
[4]: https://github.com/DataDog/integrations-core/blob/master/falco/datadog_checks/falco/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/configuration/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/containers/kubernetes/integrations/
[7]: https://docs.datadoghq.com/getting_started/site/#access-the-datadog-site

