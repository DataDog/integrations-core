# Istio check

## Overview

Datadog monitors every aspect of your Istio environment, so you can:
- Assess the health of Envoy and the Istio control plane with logs ([see below](#log-collection)).
- Break down the performance of your service mesh with request, bandwidth, and resource consumption metrics ([see below](#metrics)).
- Map network communication between containers, pods, and services over the mesh with [Network Performance Monitoring][19].
- Drill into distributed traces for applications transacting over the mesh with [APM][20].

To learn more about monitoring your Istio environment with Datadog, [see the Istio blog][21].

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][1] for guidance on applying these instructions.

### Installation

Istio is included in the Datadog Agent. [Install the Datadog Agent][2] on your Istio servers or in your cluster and point it at Istio.

### Configuration

Edit the `istio.d/conf.yaml` file (in the `conf.d/` folder at the root of your [Agent's configuration directory][3]) to connect to Istio. See the [sample istio.d/conf.yaml][4] for all available configuration options.

#### Metric Collection

Add one of the configuration blocks below to your `istio.d/conf.yaml` file to start gathering your Istio Metrics for your supported version:

1. To monitor the `istiod` deployment in Istio `v1.5+`, use the following configuration:
    
    ```yaml
    init_config:
    
    instances:
      - istiod_endpoint: http://istiod.istio-system:15014/metrics
    ```
    
   To monitor Istio mesh metrics, continue to use `istio_mesh_endpoint`. Istio mesh metrics are now only available from `istio-proxy` containers which are supported out-of-the-box via autodiscovery, see [`istio.d/auto_conf.yaml`][17].
   
   **NOTE**: Be sure to enable [V1 Telemetry][18] for Istio `v1.6` or higher to collect mesh metrics.
   
2. To monitor Istio versions `v1.4` or earlier, use the following configuration:
    ```yaml
    init_config:

    instances:
      - istio_mesh_endpoint: http://istio-telemetry.istio-system:42422/metrics
        mixer_endpoint: http://istio-telemetry.istio-system:15014/metrics
        galley_endpoint: http://istio-galley.istio-system:15014/metrics
        pilot_endpoint: http://istio-pilot.istio-system:15014/metrics
        citadel_endpoint: http://istio-citadel.istio-system:15014/metrics
        send_histograms_buckets: true
    ```

Each of the endpoints is optional, but at least one must be configured. See the [Istio documentation][5] to learn more about the Prometheus adapter.

Note: `connectionID` Prometheus label is excluded.

##### Disable sidecar injection for Datadog Agent pods

If you are installing the [Datadog Agent in a container][10], Datadog recommends that you first disable Istio's sidecar injection.

Add the `sidecar.istio.io/inject: "false"` annotation to the `datadog-agent` DaemonSet:

```yaml
...
spec:
   ...
  template:
    metadata:
      annotations:
        sidecar.istio.io/inject: "false"
     ...
```

This can also be done with the `kubectl patch` command.

```text
kubectl patch daemonset datadog-agent -p '{"spec":{"template":{"metadata":{"annotations":{"sidecar.istio.io/inject":"false"}}}}}'
```

#### Log collection

Istio contains two types of logs. Envoy access logs that are collected with the [Envoy integration][12] and [Istio logs][11].

_Available for Agent versions >6.0_

See the [Autodiscovery Integration Templates][1] for guidance on applying the parameters below.
Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes log collection documentation][16].

| Parameter      | Value                                                |
| -------------- | ---------------------------------------------------- |
| `<LOG_CONFIG>` | `{"source": "istio", "service": "<SERVICE_NAME>"}` |

### Validation

[Run the Agent's `info` subcommand][6] and look for `istio` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this check.

### Events

The Istio check does not include any events.

### Service Checks

For Istio versions `1.5` or higher:

**istio.prometheus.health**:<br>
Returns `CRITICAL` if the Agent cannot reach the metrics endpoints, `OK` otherwise.

For all other versions of Istio:

**istio.pilot.prometheus.health**:<br>
Returns `CRITICAL` if the Agent cannot reach the metrics endpoints, `OK` otherwise.

**istio.galley.prometheus.health**:<br>
Returns `CRITICAL` if the Agent cannot reach the metrics endpoints, `OK` otherwise.

**istio.citadel.prometheus.health**:<br>
Returns `CRITICAL` if the Agent cannot reach the metrics endpoints, `OK` otherwise.

## Troubleshooting

Need help? Contact [Datadog support][8].

## Further Reading

Additional helpful documentation, links, and articles:

- [Monitor your Istio service mesh with Datadog][9]
- [Learn how Datadog collects key metrics to monitor Istio][14]
- [How to monitor Istio with Datadog][21]

[1]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/istio/datadog_checks/istio/data/conf.yaml.example
[5]: https://istio.io/docs/tasks/telemetry/metrics/querying-metrics
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/istio/metadata.csv
[8]: https://docs.datadoghq.com/help/
[9]: https://www.datadoghq.com/blog/monitor-istio-with-datadog
[10]: https://docs.datadoghq.com/agent/kubernetes/
[11]: https://istio.io/docs/tasks/telemetry/logs/collecting-logs/
[12]: https://docs.datadoghq.com/integrations/envoy/#log-collection
[13]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[14]: https://www.datadoghq.com/blog/istio-metrics/
[15]: https://docs.datadoghq.com/agent/guide/integration-management/#install
[16]: https://docs.datadoghq.com/agent/kubernetes/log/
[17]: https://github.com/DataDog/integrations-core/blob/master/istio/datadog_checks/istio/data/auto_conf.yaml
[18]: https://istio.io/v1.1/docs/tasks/telemetry/
[19]: https://www.datadoghq.com/blog/monitor-istio-with-npm/
[20]: https://docs.datadoghq.com/tracing/setup_overview/proxy_setup/?tab=istio
[21]: https://www.datadoghq.com/blog/istio-datadog/
