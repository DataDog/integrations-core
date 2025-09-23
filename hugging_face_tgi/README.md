# Agent Check: Hugging Face TGI

## Overview

This check monitors [Hugging Face Text Generation Inference (TGI)][1] through the Datadog Agent. TGI is a library for deploying and serving large language models (LLMs) optimized for text generation. It provides features such as continuous batching, tensor parallelism, token streaming, and optimizations for production use.

The integration provides comprehensive monitoring of your TGI servers by collecting:
- Request performance metrics, including latency, throughput, and token generation rates
- Batch processing metrics for inference optimization insights
- Queue depth and request flow monitoring
- Model serving health and operational metrics

This enables teams to optimize LLM inference performance, track resource utilization, troubleshoot bottlenecks, and ensure reliable model serving at scale.

## Setup

Follow these instructions to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The Hugging Face TGI check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

#### Metrics

1. Ensure that your TGI server exposes Prometheus metrics on the default `/metrics` endpoint. For more information, see the [TGI monitoring documentation][10].

2. Edit `hugging_face_tgi.d/conf.yaml`, located in the `conf.d/` folder at the root of your [Agent's configuration directory][11], to start collecting Hugging Face TGI performance data. See the [sample configuration file][4] for all available options.

   ```yaml
   instances:
     - openmetrics_endpoint: http://localhost:80/metrics
   ```

3. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `hugging_face_tgi` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

Key metrics include:

- **Request metrics**: Total requests, successful requests, failed requests, and request duration
- **Queue metrics**: Queue size and queue duration for monitoring throughput bottlenecks
- **Token metrics**: Generated tokens, input length, and mean time per token for performance analysis
- **Batch metrics**: Batch size, batch concatenation, and batch processing durations for optimization insights
- **Inference metrics**: Forward pass duration, decode duration, and filter duration for model performance monitoring

### Events

The Hugging Face TGI integration does not include any events.

### Service Checks

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

In containerized environments, ensure that the Agent has network access to the TGI metrics endpoint specified in `hugging_face_tgi.d/conf.yaml`.

Need help? Contact [Datadog support][9].


[1]: https://huggingface.co/docs/text-generation-inference/index
[2]: /account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/hugging_face_tgi/datadog_checks/hugging_face_tgi/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/hugging_face_tgi/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/hugging_face_tgi/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://huggingface.co/docs/text-generation-inference/en/basic_tutorials/monitoring
[11]: https://docs.datadoghq.com/agent/configuration/agent-configuration-files/#agent-configuration-directory
