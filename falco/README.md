# Falco Integration For Datadog

## Overview

[Falco][1] is a cloud-native security tool. It provides near real-time threat detection for cloud, container, and Kubernetes workloads by leveraging runtime insights. Falco can monitor events defined via customizable rules from various sources, including the Linux kernel, and enrich them with metadata from the Kubernetes API server, container runtime, and more.
This integration ingests the following logs:

- Alert: Represents details such as the rule name, description, condition, output message, priority level, and tags

The Falco integration seamlessly ingests the data of Falco logs using the Webhook. Before ingestion of the data, it normalizes and enriches the logs, ensuring a consistent data format and enhancing information content for downstream processing and analysis. The integration provides insights into alert logs through the out-of-the-box dashboards.

## Setup

### Configuration

#### Falco Integration Configuration

- Update the settings in the configuration file (i.e., falco.yaml) as shown below:

  ```json_output: true
  http_output:
    enabled: true
    url: <Datadog Webhook URL> (e.g., https://http-intake.logs.datadoghq.com/api/v2/logs?dd-api-key=<dd-api-key>&ddsource=falco)
  ```

- If Falco is installed using Helm, you can use the following command to add or update the HTTP URL:

  ```helm upgrade -i falco falcosecurity/falco \
    --set falco.http_output.enabled=true \
    --set falco.http_output.url="https://http-intake.logs.datadoghq.com/api/v2/logs?dd-api-key=<dd-api-key>&ddsource=falco" \
    --set falco.json_output=true \
    --set json_include_output_property=true
  ```

## Data Collected

### Logs

The Falco integration collects and forwards Falco Alert logs to Datadog.

### Metrics

The Falco integration does not include any metrics.

### Events

The Falco integration does not include any events.

## Support

For further assistance, contact [Datadog Support][2].

[1]: https://falco.org/docs/getting-started/
[2]: https://docs.datadoghq.com/help/