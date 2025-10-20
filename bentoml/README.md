# Agent Check: BentoML

## Overview

This check monitors [BentoML][1] through the Datadog Agent.

BentoML is an open-source platform for building, shipping, and running machine learning models in production. This integration enables you to track the health and performance of your BentoML model serving infrastructure directly from Datadog.

By using this integration, you gain visibility into key BentoML metrics such as request throughput, response latency, error rates, and resource utilization. Monitoring these metrics helps you ensure reliable model deployments, quickly detect issues, and optimize the performance of your ML services in production environments.

**Minimum Agent version:** 7.70.1

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

Starting with Agent version `7.71.0`, the BentoML check is included in the [Datadog Agent][2] package. No additional installation is needed on your environment. 

### Configuration

#### Metrics

The BentoML integration collects data from both the [health API endpoints][11] and the [Prometheus metrics endpoint][10]. By default, BentoML exposes these endpoints, so in most cases, no additional configuration is required on the BentoML side. For more information about these endpoints and how to enable or secure them, refer to the [BentoML observability documentation][11].

To configure the Datadog Agent to collect BentoML metrics:

1. Edit the `bentoml.d/conf.yaml` file, located in the `conf.d/` directory at the root of your Agent's configuration folder. This file controls how the Agent collects metrics from your BentoML deployment. For a full list of configuration options, see the [sample bentoml.d/conf.yaml][4]. Below is a minimal example configuration:

```yaml
init_config:
instances:
  - openmetrics_endpoint: http://localhost:3000/metrics
    tags:
    - bentoml_service: foo # Tag to easily scope metrics
```

2. [Restart the Agent][5].

#### Logs

BentoML logs can be collected by the Datadog Agent using several methods:

- **Agent log collection (recommended)**: Configure the Datadog Agent to tail BentoML log files. See the [BentoML documentation][12] for more details.

**For host-based Agents:**

1. Enable log collection in your `datadog.yaml` file (disabled by default):

    ```yaml
    logs_enabled: true
    ```

2. Configure the Agent to tail BentoML logs by editing `bentoml.d/conf.yaml` (or the corresponding file in `conf.d/`):

    ```yaml
    logs:
      - type: file
        path: monitoring/text_summarization/data/*.log
        source: bentoml
        service: <SERVICE>
    ```

   Replace `<SERVICE>` with a name that matches your service.

**For containerized environments**:

- Ensure the BentoML log files are mounted inside the Datadog Agent container so they can be accessed and tailed. See [container based log collection][14] for more information.

**Other log shipping options**:

- **Fluent Bit**: Forward logs to Datadog using [Fluent Bit][13].
- **OTLP**: Send logs to the Datadog Agent using the [OpenTelemetry Protocol (OTLP)][14].

Choose the log collection method that best fits your environment and operational needs. Ensure the logs are tagged correctly with `source:bentoml`.

### Validation

[Run the Agent's status subcommand][6] and look for `bentoml` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The BentoML integration does not include any events.

### Service Checks

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: https://docs.bentoml.com/en/latest/index.html
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/containers/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/bentoml/datadog_checks/bentoml/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/configuration/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/configuration/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/bentoml/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/bentoml/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://docs.bentoml.com/en/latest/build-with-bentoml/observability/metrics.html
[11]: https://docs.bentoml.com/en/latest/build-with-bentoml/observability/monitoring-and-data-collection.html#monitoring
[12]: https://docs.bentoml.com/en/latest/build-with-bentoml/observability/monitoring-and-data-collection.html#view-request-and-schema-logs
[13]: https://docs.fluentbit.io/manual/data-pipeline/outputs/datadog
[14]: https://docs.datadoghq.com/opentelemetry/setup/otlp_ingest_in_the_agent/?tab=docker#enabling-otlp-ingestion-on-the-datadog-agent
