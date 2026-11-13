# Agent Check: llm-d

## Overview

[llm-d][1] is a Kubernetes-native distributed inference stack that routes requests across model servers
with an Endpoint Picker (EPP), and splits inference into prefill and decode stages with a prefill/decode (P/D) sidecar.
This check collects Prometheus metrics from the llm-d components:

- **Router (EPP)**: request throughput, errors and outcomes, time to first token, inter-token latency,
  token counts, InferencePool load, scheduling, prefix cache, KV-cache index, and Flow Control metrics
- **P/D sidecar**: disaggregated requests, and encode, prefill, and decode stage latency and errors
- **Coordinator**: request, pipeline step, and upstream call metrics

Model server metrics are collected by the [vLLM][2] or [SGLang][3] integrations.

Histogram buckets are submitted as Datadog distributions by default, so percentile aggregations are
available for latency and token-count metrics.

This integration is part of [GPU Monitoring][4] and runs only when GPU Monitoring is enabled.

**Minimum Agent version:** 7.87.0

**Supported llm-d versions:** v1.0.0 and later

## Setup

Use the following instructions to configure this check for an Agent running on Kubernetes. See the
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

The EPP serves metrics on port 9090 of the `epp` container. Metrics endpoint authentication
(`--metrics-endpoint-auth`) is enabled by default, so the EPP only accepts bearer tokens from identities with
`get` permission on the `/metrics` non-resource URL. To grant this permission to the Agent's ServiceAccount,
create a ClusterRole and ClusterRoleBinding:

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

Replace `<AGENT_NAMESPACE>` with the namespace the Agent runs in, and `<AGENT_SERVICE_ACCOUNT>` with the
Agent's ServiceAccount. With the Datadog Helm chart, the ServiceAccount is named after the release (for
example, `datadog` for a release named `datadog`). With the Datadog Operator, it is
`<DATADOGAGENT_NAME>-agent` (for example, `datadog-agent`).

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

Keep `<TOKEN>` as written. The Agent replaces it with the token it reads from the file.

To serve `/metrics` without authentication instead, install the llm-d router chart with
`router.monitoring.prometheus.auth.enabled: false` and omit `auth_token`.

#### P/D sidecar

The sidecar metrics endpoint is disabled by default. Start the sidecar with `--metrics-port` (for example,
`--metrics-port=9090`) and add an instance for that port on the sidecar container.

#### Coordinator

The coordinator serves unauthenticated metrics on its metrics port (default 9090). Add an instance for
that port on the coordinator container.

#### Model servers

Collect model server metrics with the vLLM or SGLang integration. On decode pods that run the P/D sidecar,
the sidecar listens on port 8000 and vLLM listens on the model server port (default 8200). Point the vLLM
check at the model server port, not the sidecar port.

#### Tags

EPP request metrics (`llm_d.epp.request.*`) don't include an InferencePool label. To group metrics by
InferencePool, tag the router and model server pods with the InferencePool name:

```yaml
metadata:
  annotations:
    ad.datadoghq.com/tags: '{"inference_pool": "<INFERENCE_POOL_NAME>"}'
```

To tag model server metrics with their disaggregation role, map the `llm-d.ai/role` pod label to the
`llm_d_role` tag. Set `datadog.podLabelsAsTags` in the Datadog Helm chart, or
`spec.global.podLabelsAsTags` in the Datadog Operator:

```yaml
podLabelsAsTags:
  llm-d.ai/role: llm_d_role
```

### Validation

Run the [Agent status command][8] and look for `llm_d` under the Checks section.

## Data collected

### Metrics

See [metadata.csv][9] for a list of metrics provided by this integration.

The integration renames the following labels:

- `name` (the InferencePool name) becomes `inference_pool`.
- `namespace` becomes `endpoint_namespace`.
- `port` becomes `endpoint_port`.

The `namespace` and `port` labels describe the model server endpoint that a request was scheduled to, not the
scraped pod.

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
