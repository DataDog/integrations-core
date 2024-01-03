# Linkerd Integration

## Overview

[Linkerd][1] is a light but powerful open-source service mesh with CNCF graduated status. It provides the tools you need to write secure, reliable, observable cloud-native applications. With minimal configuration and no application changes, Linkerd:
- Uses mutual TLS to transparently secure all on-cluster TCP communication. 
- Adds latency-aware load balancing, request retries, timeouts, and blue-green deploys to keep your applications resilient.
- Provides platform health metrics by tracking success rates, latencies, and request volumes for every meshed workload.

This integration sends your Linkerd metrics to Datadog, including application success rates, latency, and saturation.


## Setup

This OpenMetrics-based integration has a latest mode (enabled by setting `openmetrics_endpoint` to point to the target endpoint) and a legacy mode (enabled by setting `prometheus_url` instead). To get all the most up-to-date features, Datadog recommends enabling the latest mode. For more information, see [Latest and Legacy Versioning For OpenMetrics-based Integrations][16].

Metrics marked as `[OpenMetrics V1]` or `[OpenMetrics V2]` are only available using the corresponding mode of the Linkerd integration. Metrics not marked are collected by all modes.

### Installation

The Linkerd check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your server.

### Configuration

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

1. Edit the `linkerd.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][3].
   See the [sample `linkerd.d/conf.yaml`][4] for all available configuration options using the latest OpenMetrics check example. If you previously implemented this integration, see the [legacy example][5].

2. [Restart the Agent][6].

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][7] for guidance on applying the parameters below.

##### Linkerd v1

| Parameter            | Value                                                                       |
| -------------------- | --------------------------------------------------------------------------- |
| `<INTEGRATION_NAME>` | `linkerd`                                                                   |
| `<INIT_CONFIG>`      | blank or `{}`                                                               |
| `<INSTANCE_CONFIG>`  | `{"openmetrics_endpoint": "http://%%host%%:9990/admin/metrics/prometheus"}` |

 **Note**: This is a new default OpenMetrics check example. If you previously implemented this integration, see the [legacy example][5].

##### Linkerd v2

| Parameter            | Value                                                                       |
| -------------------- | --------------------------------------------------------------------------- |
| `<INTEGRATION_NAME>` | `linkerd`                                                                   |
| `<INIT_CONFIG>`      | blank or `{}`                                                               |
| `<INSTANCE_CONFIG>`  | `{"openmetrics_endpoint": "http://%%host%%:4191/metrics"}`                  |

   **Note**: This is a new default OpenMetrics check example. If you previously implemented this integration, see the [legacy example][5].


##### Log collection

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes log collection][8].

| Parameter      | Value                                                |
| -------------- | ---------------------------------------------------- |
| `<LOG_CONFIG>` | `{"source": "linkerd", "service": "<SERVICE_NAME>"}` |

To increase the verbosity of the data plane logs, see [Modifying the Proxy Log Level][9].

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

Run the [Agent's status subcommand][10] and look for `linkerd` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][11] for a list of metrics provided by this integration.

For Linkerd v1, see the [finagle metrics guide][12] for metric descriptions and [this gist][13] for an example of metrics exposed by Linkerd.

Linkerd is a Prometheus-based integration. Depending on your Linkerd configuration, some metrics might not be exposed by Linkerd. If any metric is not present in the cURL output, the Datadog Agent is unable to collect that particular metric.

To list the metrics exposed by your current configuration, run:

```bash
curl <linkerd_prometheus_endpoint>
```

Where `linkerd_prometheus_endpoint` is the Linkerd Prometheus endpoint (you should use the same value as the `prometheus_url` config key in your `linkerd.yaml`)

If you need to use a metric that is not provided by default, you can add an entry to `linkerd.yaml`.

For more information, see the examples in the [default configuration][4].


### Service Checks

See [service_checks.json][14] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][15].


[1]: https://linkerd.io
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/linkerd/datadog_checks/linkerd/data/conf.yaml.example
[5]: https://github.com/DataDog/integrations-core/blob/7.30.x/linkerd/datadog_checks/linkerd/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6v7#restart-the-agent
[7]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[8]: https://docs.datadoghq.com/agent/kubernetes/log/
[9]: https://linkerd.io/2/tasks/modifying-proxy-log-level/
[10]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[11]: https://github.com/DataDog/integrations-core/blob/master/linkerd/metadata.csv
[12]: https://twitter.github.io/finagle/guide/Metrics.html
[13]: https://gist.githubusercontent.com/arbll/2f63a5375a4d6d5acface6ca8a51e2ab/raw/bc35ed4f0f4bac7e2643a6009f45f9068f4c1d12/gistfile1.txt
[14]: https://github.com/DataDog/integrations-core/blob/master/linkerd/assets/service_checks.json
[15]: https://docs.datadoghq.com/help/
[16]: https://docs.datadoghq.com/integrations/guide/versions-for-openmetrics-based-integrations