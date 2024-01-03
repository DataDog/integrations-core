# Agent Check: Nvidia Triton

## Overview

This check monitors [Nvidia Triton][1] through the Datadog Agent.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The Nvidia Triton check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

#### OpenMetrics endpoint

By default, the Nvidia Triton server exposes all metrics through the Prometheus endpoint.
To enable all metrics reportings:

```
tritonserver --allow-metrics=true
```

To change the metric endpoint, use the `--metrics-address` option.

Example:

```
tritonserver --metrics-address=http://0.0.0.0:8002
```

In this case, the OpenMetrics endpoint is exposed at this URL: `http://<NVIDIA_TRITON_ADDRESS>:8002/metrics`.

The [latency summary][10] metrics are disabled by default. To enable summary metrics for latencies, use the command below:

```
tritonserver --metrics-config summary_latencies=true
```

The [response cache metrics][11] are not reported by default. You need to enable a cache implementation on the server side by specifying a <cache_implementation> and corresponding configuration.

For instance:

```
tritonserver --cache-config local,size=1048576
```

Nvidia Triton also offers the possibility to expose [custom metrics][12] through their Openemtrics endpoint. Datadog can also collect these custom metrics using the `extra_metrics` option.
<div class="alert alert-warning">These custom Nvidia Triton metrics are considered standard metrics in Datadog.</div>

### Configuration

1. Edit the `nvidia_triton.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your nvidia_triton performance data. See the [sample nvidia_triton.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `nvidia_triton` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The Nvidia Triton integration does not include any events.

### Service Checks

The Nvidia Triton integration includes two service checks.

See [service_checks.json][8] for a list of service checks provided by this integration.

### Logs

The Nvidia Triton integration can collect logs from the Nvidia Triton server and forward them to Datadog.

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

2. Uncomment and edit the logs configuration block in your `nvidia_triton.d/conf.yaml` file. Here's an example:

   ```yaml
   logs:
     - type: docker
       source: nvidia_triton
       service: nvidia_triton
   ```

<!-- xxz tab xxx -->
<!-- xxx tab "Kubernetes" xxx -->

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes Log Collection][13].

Then, set Log Integrations as pod annotations. This can also be configured with a file, a configmap, or a key-value store. For more information, see the configuration section of [Kubernetes Log Collection][14].


**Annotations v1/v2**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: nvidia_triton
  annotations:
    ad.datadoghq.com/apache.logs: '[{"source":"nvidia_triton","service":"nvidia_triton"}]'
spec:
  containers:
    - name: ray
```

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->


## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: https://www.nvidia.com/en-us/ai-data-science/products/triton-inference-server/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/nvidia_triton/datadog_checks/nvidia_triton/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/nvidia_triton/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/nvidia_triton/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/user_guide/metrics.html#summaries
[11]: https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/user_guide/metrics.html#response-cache-metrics
[12]: https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/user_guide/metrics.html#custom-metrics
[13]: https://docs.datadoghq.com/agent/kubernetes/log/#setup
[14]: https://docs.datadoghq.com/agent/kubernetes/log/#configuration
