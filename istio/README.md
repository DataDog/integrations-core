# Istio check

## Overview

Datadog monitors every aspect of your Istio environment, so you can:
- Assess the health of Envoy and the Istio control plane with logs ([see below](#log-collection)).
- Break down the performance of your service mesh with request, bandwidth, and resource consumption metrics ([see below](#metrics)).
- Map network communication between containers, pods, and services over the mesh with [Network Performance Monitoring][1].
- Drill into distributed traces for applications transacting over the mesh with [APM][2].

To learn more about monitoring your Istio environment with Datadog, [see the Istio blog][3].

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][4] for guidance on applying these instructions.

### Installation

Istio is included in the Datadog Agent. [Install the Datadog Agent][5] on your Istio servers or in your cluster and point it at Istio.

#### Envoy

If you want to monitor the Envoy proxies in Istio, configure the [Envoy integration][6].

### Configuration

Edit the `istio.d/conf.yaml` file (in the `conf.d/` folder at the root of your [Agent's configuration directory][7]) to connect to Istio. See the [sample istio.d/conf.yaml][8] for all available configuration options.

#### Metric collection
To monitor the `istiod` deployment and `istio-proxy` in Istio `v1.5+`, use the following configuration:
    
    ```yaml
    init_config:
    
    instances:
      - use_openmetrics: true  # Enables Openmetrics V2 version of the integration
      - istiod_endpoint: http://istiod.istio-system:15014/metrics
      - istio_mesh_endpoint: http://istio-proxy.istio-system:15090/stats/prometheus
        exclude_labels:
         - source_version
         - destination_version
         - source_canonical_revision
         - destination_canonical_revision
         - source_principal
         - destination_principal
         - source_cluster
         - destination_cluster
         - source_canonical_service
         - destination_canonical_service
         - source_workload_namespace
         - destination_workload_namespace
         - request_protocol
         - connection_security_policy
    ```
   
**Note**: The `connectionID` Prometheus label is excluded. The [sample istio.d/conf.yaml][8] also has a list of suggested labels to exclude.


   Istio mesh metrics are now only available from `istio-proxy` containers which are supported out-of-the-box via autodiscovery, see [`istio.d/auto_conf.yaml`][9].   

##### OpenMetrics V2 vs OpenMetrics V1
<div class="alert alert-warning">
<b>Important Note</b>: If you have multiple instances of Datadog collecting Istio metrics, make sure to use the same implementation of OpenMetrics for all of them. Otherwise, the metrics data will fluctuate in the Datadog app.
</div>

When you enable the `use_openmetrics` configuration option, the Istio integration uses the OpenMetrics V2 implementation of the check. 

In OpenMetrics V2, metrics are submitted more accurately by default and behave closer to Prometheus metric types. For example, Prometheus metrics ending in  `_count` and `_sum` are now submitted as `monotonic_count` by default.

OpenMetrics V2 addresses performance and quality issues in OpenMetrics V1. Updates include native metric types support, improved configuration, and custom metric types.

Set the `use_openmetrics` configuration option to `false` to use the OpenMetrics V1 implementation. To view the configuration parameters for OpenMetrics V1, see [the `conf.yaml.example` file][21].


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

<!-- partial
{{< site-region region="us3" >}}
**Log collection is not supported for the Datadog {{< region-param key="dd_site_name" >}} site**.
{{< /site-region >}}
partial -->

Istio contains two types of logs. Envoy access logs that are collected with the [Envoy integration][11] and [Istio logs][12].

_Available for Agent versions >6.0_

See the [Autodiscovery Integration Templates][4] for guidance on applying the parameters below.
Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes log collection documentation][13].

| Parameter      | Value                                                |
| -------------- | ---------------------------------------------------- |
| `<LOG_CONFIG>` | `{"source": "istio", "service": "<SERVICE_NAME>"}` |

### Validation

[Run the Agent's `info` subcommand][14] and look for `istio` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][15] for a list of metrics provided by this check.

### Events

The Istio check does not include any events.

### Service Checks

See [service_checks.json][16] for a list of service checks provided by this integration.

## Troubleshooting

### Invalid chunk length error
If you see the following error on OpenMetricsBaseCheck (V1) implementation of Istio (Istio integration version `3.13.0` or older):

    ```python
      Error: ("Connection broken: InvalidChunkLength(got length b'', 0 bytes read)", 
      InvalidChunkLength(got length b'', 0 bytes read))
    ```

You can use the Openmetrics V2 implementation of the Istio integration to resolve this error.

Note: you must upgrade to at minimum Agent `7.31.0` and Python 3. See the [Configuration](#configuration) section on enabling Openmetrics V2.


### Using the generic Openmetrics Integration in an Istio deployment

If Istio proxy sidecar injection is enabled, monitoring other Prometheus metrics via the [Openmetrics integration][20] with the same metrics endpoint as `istio_mesh_endpoint` can result in high custom metrics usage and duplicated metric collection.

To ensure that your Openmetrics configuration does not redundantly collect metrics, either:

1. Use specific metric matching in the `metrics` configuration option, or
2. If using the wildcard `*` value for `metrics`, consider using the following Openmetrics integration options to exclude metrics already supported by the Istio and Envoy integrations.

#### Openmetrics V2 configuration with generic metric collection

Be sure to exclude Istio and Envoy metrics from your configuration to avoid high custom metrics billing. Use `exclude_metrics` if using the Openmetrics V2 configuration (`openmetrics_endpoint` enabled).
 
```yaml
## Every instance is scheduled independent of the others.
#
instances:
  - openmetrics_endpoint: <OPENMETRICS_ENDPOINT>
    metrics: [*]
    exclude_metrics:
      - istio_*
      - envoy_*

```

#### Openmetrics V1 configuration (Legacy) with generic metric collection

Be sure to exclude Istio and Envoy metrics from your configuration to avoid high custom metrics billing. Use `ignore_metrics` if using the Openmetrics V1 configuration (`prometheus_url` enabled).

```yaml
instances:
  - prometheus_url: <PROMETHEUS_URL>
    metrics:
      - *
    ignore_metrics:
      - istio_*
      - envoy_*
```

Need help? Contact [Datadog support][17].

## Further Reading

Additional helpful documentation, links, and articles:

- [Monitor your Istio service mesh with Datadog][18]
- [Learn how Datadog collects key metrics to monitor Istio][19]
- [How to monitor Istio with Datadog][16]

[1]: https://www.datadoghq.com/blog/monitor-istio-with-npm/
[2]: https://docs.datadoghq.com/tracing/setup_overview/proxy_setup/?tab=istio
[3]: https://www.datadoghq.com/blog/istio-datadog/
[4]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[5]: https://app.datadoghq.com/account/settings#agent
[6]: https://github.com/DataDog/integrations-core/tree/master/envoy#istio
[7]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[8]: https://github.com/DataDog/integrations-core/blob/master/istio/datadog_checks/istio/data/conf.yaml.example
[9]: https://github.com/DataDog/integrations-core/blob/master/istio/datadog_checks/istio/data/auto_conf.yaml
[10]: https://docs.datadoghq.com/agent/kubernetes/
[11]: https://docs.datadoghq.com/integrations/envoy/#log-collection
[12]: https://istio.io/docs/tasks/telemetry/logs/collecting-logs/
[13]: https://docs.datadoghq.com/agent/kubernetes/log/
[14]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[15]: https://github.com/DataDog/integrations-core/blob/master/istio/metadata.csv
[16]: https://github.com/DataDog/integrations-core/blob/master/istio/assets/service_checks.json
[17]: https://docs.datadoghq.com/help/
[18]: https://www.datadoghq.com/blog/monitor-istio-with-datadog
[19]: https://www.datadoghq.com/blog/istio-metrics/
[20]: https://docs.datadoghq.com/integrations/openmetrics/
[21]: https://github.com/DataDog/integrations-core/blob/7.32.x/istio/datadog_checks/istio/data/conf.yaml.example
