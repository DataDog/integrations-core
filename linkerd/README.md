# Linkerd Integration

## Overview

This check collects distributed system observability metrics from [Linkerd][1].

## Setup

### Installation

The Linkerd check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your server.

### Configuration

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

1. Edit the `linkerd.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][3].
   See [sample linkerd.d/conf.yaml][4] for all available configuration options.
   **Note**: This is a new default OpenMetrics check example. If you previously implemented this integration, see the [legacy example][5].

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

<!-- partial
{{< site-region region="us3" >}}
**Log collection is not supported for the Datadog {{< region-param key="dd_site_name" >}} site**.
{{< /site-region >}}
partial -->

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes log collection][8].

| Parameter      | Value                                                |
| -------------- | ---------------------------------------------------- |
| `<LOG_CONFIG>` | `{"source": "linkerd", "service": "<SERVICE_NAME>"}` |

To increase the verbosity of the data plane logs, see [the official Linkerd documentation][9].

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's status subcommand][10] and look for `linkerd` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][11] for a list of metrics provided by this integration.

For linkerd v1, see [finagle metrics docs][12] for a detailed description of some of the available metrics and [this gist][13] for an example of metrics exposed by linkerd.

Attention: Depending on your linkerd configuration, some metrics might not be exposed by linkerd.

To list the metrics exposed by your current configuration, run

```bash
curl <linkerd_prometheus_endpoint>
```

Where `linkerd_prometheus_endpoint` is the linkerd prometheus endpoint (you should use the same value as the `prometheus_url` config key in your `linkerd.yaml`)

If you need to use a metric that is not provided by default, you can add an entry to `linkerd.yaml`.

Simply follow the examples present in the [default configuration][4].

### Service Checks

See [service_checks.json][14] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][15].


[1]: https://linkerd.io
[2]: https://app.datadoghq.com/account/settings#agent
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
