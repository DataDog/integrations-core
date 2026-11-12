# Agent Check: llm-d

## Overview

[llm-d][1] is a Kubernetes-native distributed inference stack that routes requests across model servers
with an Endpoint Picker (EPP), and splits inference into prefill and decode stages with a P/D sidecar.
This check collects Prometheus metrics from the llm-d components:

- **Router (EPP)**: request throughput, errors and outcomes, time to first token, inter-token latency,
  token counts, InferencePool load, scheduling, prefix cache, KV-cache index, and Flow Control metrics
- **P/D sidecar**: disaggregated requests, and encode, prefill, and decode stage latency and errors
- **Coordinator**: request, pipeline step, and upstream call metrics

Model server metrics are collected by the [vLLM][2] or [SGLang][3] integrations.

Histogram buckets are submitted as Datadog distributions by default, so percentile aggregations are
available for latency and token-count metrics.

This integration is part of [GPU Monitoring][4] and only runs when GPU Monitoring is enabled.

**Minimum Agent version:** 7.87.0

## Setup

Follow the instructions below to configure this check for an Agent running on Kubernetes. See the
[Autodiscovery integration templates][5] for more guidance.

### Prerequisites

Enable GPU Monitoring in the Datadog Agent configuration:

```yaml
gpu:
  enabled: true
```

The equivalent environment variable is `DD_GPU_ENABLED=true`. When GPU Monitoring is disabled, the
Agent skips every configured llm-d instance.

### Installation

The llm-d check is included in the [Datadog Agent][6] package. No additional installation is needed.

### Configuration

Configure one instance per llm-d `/metrics` endpoint. See the [sample llm_d.d/conf.yaml][7] for all
available configuration options.

#### Router (EPP)

The EPP serves its metrics on port 9090 of the `epp` container. Authentication is enabled by default
(`--metrics-endpoint-auth`): the EPP accepts bearer tokens for identities allowed to `get` the `/metrics`
non-resource URL. Grant that to the Agent's ServiceAccount:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: llm-d-metrics-reader
rules:
- nonResourceURLs: ["/metrics"]
  verbs: ["get"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: llm-d-metrics-reader
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: llm-d-metrics-reader
subjects:
- kind: ServiceAccount
  name: <AGENT_SERVICE_ACCOUNT>
  namespace: <AGENT_NAMESPACE>
```

Then annotate the router pod so the Agent sends its ServiceAccount token:

```yaml
metadata:
  annotations:
    ad.datadoghq.com/epp.checks: |
      {
        "llm_d": {
          "instances": [
            {
              "openmetrics_endpoint": "http://%%host%%:9090/metrics",
              "auth_token": {
                "reader": {"type": "file", "path": "/var/run/secrets/kubernetes.io/serviceaccount/token"},
                "writer": {"type": "header", "name": "Authorization", "value": "Bearer <TOKEN>"}
              }
            }
          ]
        }
      }
```

To serve `/metrics` without authentication instead, install the llm-d router chart with
`router.monitoring.prometheus.auth.enabled: false` and omit `auth_token`.

#### P/D sidecar

The sidecar metrics endpoint is disabled by default. Start the sidecar with `--metrics-port` (for example,
`--metrics-port=9090`) and add an instance for that port on the sidecar container.

#### Coordinator

The coordinator serves unauthenticated metrics on its metrics port (default 9090). Add an instance for
that port on the coordinator container.

#### Model servers

Collect engine metrics with the vLLM or SGLang integration. On decode pods that run the P/D sidecar, the
sidecar listens on port 8000 and vLLM listens on the model server port (default 8200), so point the
vLLM check at port 8200.

#### Tags

Request metrics carry no InferencePool label. Tag the router and model server pods with the
InferencePool name so their metrics can be grouped by deployment:

```yaml
metadata:
  annotations:
    ad.datadoghq.com/tags: '{"inference_pool": "<INFERENCE_POOL_NAME>"}'
```

To tag model server metrics with their disaggregation role, map the `llm-d.ai/role` pod label to the
`llm_d_role` tag. With the Datadog Helm chart, set `datadog.podLabelsAsTags`; with the Datadog Operator,
set `spec.global.podLabelsAsTags`:

```yaml
podLabelsAsTags:
  llm-d.ai/role: llm_d_role
```

The same setting can map a pod label that holds the InferencePool name to `inference_pool`, as an
alternative to the annotation.

### Validation

Run the [Agent status command][8] and look for `llm_d` under the Checks section.

## Data collected

### Metrics

See [metadata.csv][9] for a list of metrics provided by this integration.

The integration renames these labels:

- `name`, the InferencePool name, to `inference_pool`.
- `namespace`, `port`, and the legacy `pod_name`, which describe the model server endpoint a request was
  scheduled to rather than the scraped pod, to `endpoint_namespace`, `endpoint_port`, and `endpoint_name`.
- The legacy `model_server_pod` to `model_server_endpoint`.

Legacy EPP metric names (`inference_objective_*`, `inference_pool_*`, `inference_extension_*`,
`llm_d_inference_scheduler_*`, and `kvcache_*`) are reported under the same Datadog metrics as their
`llm_d_epp_*` replacements. llm-d v0.10 emits both the legacy and current names, and v0.11 emits both
for the `kvcache_*` series. On those versions, add the legacy names to `exclude_metrics` to avoid
counting them twice.

### Events

The llm-d integration does not include any events.

### Service checks

See [service_checks.json][10] for the service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][11].


[1]: https://llm-d.ai/
[2]: https://docs.datadoghq.com/integrations/vllm/
[3]: https://docs.datadoghq.com/integrations/sglang/
[4]: https://docs.datadoghq.com/gpu_monitoring/
[5]: https://docs.datadoghq.com/containers/kubernetes/integrations/
[6]: https://app.datadoghq.com/account/settings/agent/latest
[7]: https://github.com/DataDog/integrations-core/blob/master/llm_d/datadog_checks/llm_d/data/conf.yaml.example
[8]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[9]: https://github.com/DataDog/integrations-core/blob/master/llm_d/metadata.csv
[10]: https://github.com/DataDog/integrations-core/blob/master/llm_d/assets/service_checks.json
[11]: https://docs.datadoghq.com/help/
