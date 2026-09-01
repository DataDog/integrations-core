# Agent Check: Dynamo

## Overview

[NVIDIA Dynamo][1] is an open-source, distributed inference-serving framework for large language
models. It routes requests across disaggregated prefill and decode workers, manages KV cache reuse,
and supports backends such as vLLM, SGLang, and TensorRT-LLM.

This check collects metrics from Dynamo's built-in Prometheus endpoints, giving you visibility into
request throughput, latency (including time to first token and inter-token latency), queueing, KV
cache hit rate, and worker and task health across your Dynamo deployment.

**Minimum Agent version:** 7.84.0

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host.
For containerized environments, see the [Autodiscovery integration templates][3] for guidance on
applying these instructions.

### Prerequisites

This integration is part of [GPU monitoring][10] and only runs when GPU monitoring is enabled in the
Datadog Agent configuration:

```yaml
gpu:
  enabled: true
```

The equivalent environment variable is `DD_GPU_ENABLED=true`. When GPU monitoring is off, the check
skips every configured instance and reports no metrics.

### Installation

The Dynamo check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

Dynamo exposes Prometheus metrics from two kinds of components, each of which must be configured as
its own instance if you want both:

- The **frontend** (default port `8000`), which exposes request-level metrics such as throughput,
  latency, time to first token, and KV cache hit rate under the `dynamo.frontend.*` namespace.
- **Backend workers** (`python -m dynamo.vllm`, `python -m dynamo.sglang`, `python -m dynamo.trtllm`,
  etc.), which expose a separate system status server enabled via the `DYN_SYSTEM_PORT` environment
  variable (commonly `8081` for local development, or `9090` under the Kubernetes operator). These
  report worker-level metrics such as task and queue health and KV cache block usage under the
  `dynamo.component.*` namespace.

1. Edit the `dynamo.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's
   configuration directory, to start collecting your Dynamo performance data. Point
   `openmetrics_endpoint` at the frontend's `/metrics` endpoint, and add a second instance pointed at
   a worker's system status server if you also want `dynamo.component.*` metrics. See the
   [sample dynamo.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

This check matches Dynamo's default metric names. If your deployment sets `DYN_METRICS_PREFIX` to
rename the frontend's `dynamo_frontend_` prefix, set `raw_metric_prefix` on the frontend instance to
that value so the metrics still map. Worker metrics are unaffected: Dynamo always emits those with
the `dynamo_component_` prefix.

### Validation

[Run the Agent's status subcommand][6] and look for `dynamo` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The Dynamo integration does not include any events.

### Service Checks

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: https://github.com/ai-dynamo/dynamo
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/containers/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/dynamo/datadog_checks/dynamo/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/configuration/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/configuration/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/dynamo/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/dynamo/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://docs.datadoghq.com/gpu_monitoring/
