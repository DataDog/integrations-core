# Istio check

## Overview

Datadog monitors every aspect of your Istio environment, so you can:
- Assess the health of Envoy and the Istio control plane with [logs](#log-collection).
- Break down the performance of your service mesh with [request, bandwidth, and resource consumption metrics](#metrics).
- Map network communication between containers, pods, and services over the mesh with [Network Performance Monitoring][1].
- Drill into distributed traces for applications transacting over the mesh with [APM][2].

To learn more about monitoring your Istio environment with Datadog, [see the Monitor blog post][3].

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][4] for guidance on applying these instructions.

This OpenMetrics-based integration has a latest mode (`use_openmetrics`: true) and a legacy mode (`use_openmetrics`: false). To get all the most up-to-date features, Datadog recommends enabling the latest mode. For more information, see [Latest and Legacy Versioning For OpenMetrics-based Integrations][25].

If you have multiple instances of Datadog collecting Istio metrics, make sure you are using the same mode for all of them. Otherwise, metrics data may fluctuate on the Datadog site.

Metrics marked as `[OpenMetrics V1]`, `[OpenMetrics V2]`, or `[OpenMetrics V1 and V2]` are only available using the corresponding mode of the Istio integration. Metrics marked as `Istio v1.5+` are collected using Istio version 1.5 or later.

### Installation

Istio is included in the Datadog Agent. [Install the Datadog Agent][5] on your Istio servers or in your cluster and point it at Istio.

#### Envoy

If you want to monitor the Envoy proxies in Istio, configure the [Envoy integration][6].

### Configuration

Edit the `istio.d/conf.yaml` file (in the `conf.d/` folder at the root of your [Agent's configuration directory][7]) to connect to Istio. See the [sample istio.d/conf.yaml][8] for all available configuration options.

#### Metric collection
To monitor the `istiod` deployment and `istio-proxy` in Istio `v1.5+` there are two key components involved to collect the Prometheus-formatted metrics. Aligning with the [Istio architecture][23], there is the **data plane** (the `istio-proxy` sidecar containers) and the **control plane** (the `istiod` service managing the proxies). These are both run as `istio` Agent checks, but have different responsibilities, and they are configured separately, as described below.

##### Data plane configuration
To monitor the Istio data plane, the Agent includes an [`istio.d/auto_conf.yaml`][9] file to automatically set up the monitoring for each of the `istio-proxy` sidecar containers. The Agent initializes this check for each sidecar container that it detects automatically. This configuration enables the reporting of `istio.mesh.*` metrics for the data exposed by each of these sidecar containers.

To customize the data plane portion of the integration, create an equivalent [configuration file][24] for Istio. Set `ad_identifiers` and `istio_mesh_endpoint` appropriately to set up the integration when an `istio-proxy` sidecar container is discovered. Refer to the provided [`istio.d/auto_conf.yaml`][9] and the [example configuration file][8] for all available configuration options. When you customize, set `use_openmetrics: true` and the `exclude_labels` to the following configuration:
```yaml
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

##### Control plane configuration
To monitor the Istio control plane and report the `mixer`, `galley`, `pilot`, and `citadel` metrics, you must configure the Agent to monitor the `istiod` deployment. In Istio v1.5 or later, apply the following Autodiscovery Annotations as pod annotations for the deployment `istiod` in the `istio-system` namespace:

```yaml
ad.datadoghq.com/discovery.check_names: '["istio"]'
ad.datadoghq.com/discovery.init_configs: '[{}]'
ad.datadoghq.com/discovery.instances: |
     [
       {
         "istiod_endpoint": "http://%%host%%:15014/metrics",
         "use_openmetrics": "true"
       }
     ]
```
The method for applying these annotations varies depending on the [Istio deployment strategy (Istioctl, Helm, Operator)][22] used. Consult the [Istio documentation][23] for the proper method to apply these pod annotations.

These annotations reference `discovery` as the `<CONTAINER_IDENTIFIER>` to match the default container name of the pods for the `istiod` deployment. If your container name is different, adjust accordingly.

#### Disable sidecar injection for Datadog Agent pods

If you are installing the [Datadog Agent in a container][10], Datadog recommends that you first disable Istio's sidecar injection.

_Istio versions >= 1.10:_

Add the `sidecar.istio.io/inject: "false"` **label** to the `datadog-agent` DaemonSet:

```yaml
# (...)
spec:
  template:
    metadata:
      labels:
        sidecar.istio.io/inject: "false"
    # (...)
```

This can also be done with the `kubectl patch` command.

```shell
kubectl patch daemonset datadog-agent -p '{"spec":{"template":{"metadata":{"labels":{"sidecar.istio.io/inject":"false"}}}}}'
```

_Istio versions <= 1.9:_

Add the `sidecar.istio.io/inject: "false"` **annotation** to the `datadog-agent` DaemonSet:

```yaml
# (...)
spec:
  template:
    metadata:
      annotations:
        sidecar.istio.io/inject: "false"
    # (...)
```

Using the `kubectl patch` command:

```shell
kubectl patch daemonset datadog-agent -p '{"spec":{"template":{"metadata":{"annotations":{"sidecar.istio.io/inject":"false"}}}}}'
```

#### Log collection

Istio contains two types of logs: Envoy access logs that are collected with the [Envoy integration][11] and [Istio logs][12].

_Available for Agent versions >6.0_

See the [Autodiscovery Integration Templates][4] for guidance on applying the parameters below.
Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes Log Collection][13].

| Parameter      | Value                                                |
| -------------- | ---------------------------------------------------- |
| `<LOG_CONFIG>` | `{"source": "istio", "service": "<SERVICE_NAME>"}`   |

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
If you see the following error on the legacy mode of the Istio integration (Istio integration version `3.13.0` or earlier):

```python
  Error: ("Connection broken: InvalidChunkLength(got length b'', 0 bytes read)",
  InvalidChunkLength(got length b'', 0 bytes read))
```

You can use the latest mode of the OpenMetrics-based Istio integration to resolve this error.

You must upgrade to at minimum Agent `7.31.0` and Python 3. See the [Configuration](#configuration) section to enable OpenMetrics.

### Using the generic OpenMetrics integration in an Istio deployment

If Istio proxy sidecar injection is enabled, monitoring other Prometheus metrics using the [OpenMetrics integration][20] with the same metrics endpoint as `istio_mesh_endpoint` can result in high custom metrics usage and duplicated metric collection.

To ensure that your OpenMetrics configuration does not redundantly collect metrics, either:

1. Use specific metric matching in the `metrics` configuration option, or
2. If using the wildcard `*` value for `metrics`, consider using the following OpenMetrics integration options to exclude metrics already supported by the Istio and Envoy integrations.

#### OpenMetrics latest mode configuration with generic metric collection

Be sure to exclude Istio and Envoy metrics from your configuration to avoid high custom metrics billing. Use `exclude_metrics` if `openmetrics_endpoint` is enabled.

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

#### OpenMetrics legacy mode configuration with generic metric collection

Be sure to exclude Istio and Envoy metrics from your configuration to avoid high custom metrics billing. Use `ignore_metrics` if `prometheus_url` is enabled.

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
- [How to monitor Istio with Datadog][3]

[1]: https://www.datadoghq.com/blog/monitor-istio-with-npm/
[2]: https://docs.datadoghq.com/tracing/setup_overview/proxy_setup/?tab=istio
[3]: https://www.datadoghq.com/blog/istio-datadog/
[4]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[5]: https://app.datadoghq.com/account/settings/agent/latest
[6]: https://github.com/DataDog/integrations-core/tree/master/envoy#istio
[7]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[8]: https://github.com/DataDog/integrations-core/blob/master/istio/datadog_checks/istio/data/conf.yaml.example
[9]: https://github.com/DataDog/integrations-core/blob/master/istio/datadog_checks/istio/data/auto_conf.yaml
[10]: https://docs.datadoghq.com/agent/kubernetes/
[11]: https://docs.datadoghq.com/integrations/envoy/#log-collection
[12]: https://istio.io/v1.4/docs/tasks/observability/logs/collecting-logs/
[13]: https://docs.datadoghq.com/agent/kubernetes/log/
[14]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[15]: https://github.com/DataDog/integrations-core/blob/master/istio/metadata.csv
[16]: https://github.com/DataDog/integrations-core/blob/master/istio/assets/service_checks.json
[17]: https://docs.datadoghq.com/help/
[18]: https://www.datadoghq.com/blog/monitor-istio-with-datadog
[19]: https://www.datadoghq.com/blog/istio-metrics/
[20]: https://docs.datadoghq.com/integrations/openmetrics/
[21]: https://github.com/DataDog/integrations-core/blob/7.32.x/istio/datadog_checks/istio/data/conf.yaml.example
[22]: https://istio.io/latest/docs/setup/install/
[23]: https://istio.io/latest/docs/ops/deployment/architecture/
[24]: https://docs.datadoghq.com/agent/kubernetes/integrations/?tab=file#configuration
[25]: https://docs.datadoghq.com/integrations/guide/versions-for-openmetrics-based-integrations