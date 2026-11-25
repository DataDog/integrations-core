# Agent Check: TensorRT-LLM

## Overview

[TensorRT-LLM][1] is NVIDIA's library and server (`trtllm-serve`) for serving large language models on NVIDIA GPUs.
This check collects Prometheus metrics from a `trtllm-serve` server for:

- Request and token throughput, and request errors
- Time to first token, time per output token, and end-to-end latency
- Queue, prefill, and decode time
- Running, waiting, and scheduled requests, and batch sizes
- KV cache utilization, block reuse, and host offload
- Speculative decoding acceptance
- GPU, CPU, and pinned memory usage
- Disaggregated serving and multimodal input processing

Histogram buckets are submitted as Datadog distributions by default, so percentile aggregations are
available for request latency and token-count metrics.

This integration is part of [GPU Monitoring][9] and runs only when GPU Monitoring is enabled.

**Minimum Agent version:** 7.87.0

## Setup

Follow these instructions to install and configure this check for an Agent running on a host.
For containerized environments, see the [Autodiscovery integration templates][3].

### Prerequisites

The `trtllm-serve` server exposes Prometheus metrics at `/prometheus/metrics` on its HTTP port (`8000` by default)
only when it collects per-request performance metrics: set `return_perf_metrics: true` (setting `perf_metrics_output_dir`
also enables it). Set it in the file passed to `--config` (`--extra_llm_api_options` in older releases).
Optionally, also set `enable_iter_perf_stats` to add the scheduler, batching, memory, and KV cache metrics:

```yaml
return_perf_metrics: true
enable_iter_perf_stats: true
```

Then pass the file when you start the server:

```shell
trtllm-serve <MODEL> --config config.yaml
```

Without either option, the endpoint returns an HTTP 404 error and the `tensorrt_llm.openmetrics.health` service check
reports `CRITICAL`.

Enable GPU Monitoring in the Datadog Agent configuration:

```yaml
gpu:
  enabled: true
```

The equivalent environment variable is `DD_GPU_ENABLED=true`. When GPU Monitoring is disabled, the
Agent skips every configured TensorRT-LLM instance.

### Installation

The TensorRT-LLM check is included in the [Datadog Agent][2] package. No additional installation is needed.

### Configuration

1. Edit `tensorrt_llm.d/conf.yaml` in the `conf.d/` folder at the root of the Agent configuration directory.
   Set `openmetrics_endpoint` to the server's `/prometheus/metrics` endpoint. See the
   [sample tensorrt_llm.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

For TensorRT-LLM served through NVIDIA Triton Inference Server's TensorRT-LLM backend, use the
[NVIDIA Triton integration][11] instead.

### Validation

Run the [Agent status command][6] and look for `tensorrt_llm` under the Checks section.

## Data collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

The integration drops the `pid` label that Prometheus multiprocess mode adds, because it changes every time
the server restarts.

### Events

The TensorRT-LLM integration does not include any events.

### Service checks

See [service_checks.json][8] for the service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][10].


[1]: https://nvidia.github.io/TensorRT-LLM/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/containers/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/tensorrt_llm/datadog_checks/tensorrt_llm/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/configuration/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/configuration/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/tensorrt_llm/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/tensorrt_llm/assets/service_checks.json
[9]: https://docs.datadoghq.com/gpu_monitoring/
[10]: https://docs.datadoghq.com/help/
[11]: https://docs.datadoghq.com/integrations/nvidia_triton/
