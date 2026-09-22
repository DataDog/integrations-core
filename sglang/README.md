# Agent Check: SGLang

## Overview

[SGLang][1] is a high-performance serving framework for large language models and multimodal models.
This check collects Prometheus metrics from an SGLang server for:

- Request and token throughput
- Time to first token, inter-token latency, and end-to-end latency
- Queue depth
- KV cache utilization and hit rate
- Speculative decoding efficiency
- Process resource usage

Histogram buckets are submitted as Datadog distributions by default, so percentile aggregations are
available for request latency and token-count metrics.

This integration is part of [GPU Monitoring][9] and only runs when GPU Monitoring is enabled.

**Minimum Agent version:** 7.85.0

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host.
For containerized environments, see the [Autodiscovery integration templates][3].

### Prerequisites

Enable metrics when starting the SGLang server:

```shell
sglang serve --model-path <MODEL> --enable-metrics
```

SGLang exposes metrics at `http://localhost:30000/metrics` by default.

Enable GPU Monitoring in the Datadog Agent configuration:

```yaml
gpu:
  enabled: true
```

The equivalent environment variable is `DD_GPU_ENABLED=true`. When GPU Monitoring is disabled, the
Agent skips every configured SGLang instance.

### Installation

The SGLang check is included in the [Datadog Agent][2] package. No additional installation is needed.

### Configuration

1. Edit `sglang.d/conf.yaml` in the `conf.d/` folder at the root of the Agent configuration directory.
   Set `openmetrics_endpoint` to the SGLang server's `/metrics` endpoint. See the
   [sample sglang.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

### Validation

Run the [Agent status command][6] and look for `sglang` under the Checks section.

## Data collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The SGLang integration does not include any events.

### Service checks

See [service_checks.json][8] for the service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][10].


[1]: https://docs.sglang.ai/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/containers/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/sglang/datadog_checks/sglang/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/sglang/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/sglang/assets/service_checks.json
[9]: https://docs.datadoghq.com/gpu_monitoring/
[10]: https://docs.datadoghq.com/help/
