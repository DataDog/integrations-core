# Linkerd Integration

## Overview

This check collects distributed system observability metrics from [Linkerd][1].

## Setup

### Installation

The Linkerd check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your server.

### Configuration

#### Host

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

1. Edit the `linkerd.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][3]. See [sample linkerd.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][6] for guidance on applying the parameters below.

| Parameter            | Value                                                                 |
| -------------------- | --------------------------------------------------------------------- |
| `<INTEGRATION_NAME>` | `linkerd`                                                             |
| `<INIT_CONFIG>`      | blank or `{}`                                                         |
| `<INSTANCE_CONFIG>`  | `{"prometheus_url": "http://%%host%%:9990/admin/metrics/prometheus"}` |

### Validation

[Run the Agent's status subcommand][7] and look for `linkerd` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][8] for a list of default metrics provided by this integration.

For linkerd v1, see [finagle metrics docs][9] for a detailed description of some of the available metrics and [this gist][10] for an example of metrics exposed by linkerd.

Attention: Depending on your linkerd configuration, some metrics might not be exposed by linkerd.

To list the metrics exposed by your current configuration, run

```bash
curl <linkerd_prometheus_endpoint>
```

Where `linkerd_prometheus_endpoint` is the linkerd prometheus endpoint (you should use the same value as the `prometheus_url` config key in your `linkerd.yaml`)

If you need to use a metric that is not provided by default, you can add an entry to `linkerd.yaml`.

Simply follow the examples present in the [default configuration][4].

### Service Checks

`linkerd.prometheus.health`:
Returns CRITICAL if the Agent fails to connect to the prometheus endpoint, otherwise returns UP.

## Troubleshooting

Need help? Contact [Datadog support][11].

[1]: https://linkerd.io
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/linkerd/datadog_checks/linkerd/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6v7#restart-the-agent
[6]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/linkerd/metadata.csv
[9]: https://twitter.github.io/finagle/guide/Metrics.html
[10]: https://gist.githubusercontent.com/arbll/2f63a5375a4d6d5acface6ca8a51e2ab/raw/bc35ed4f0f4bac7e2643a6009f45f9068f4c1d12/gistfile1.txt
[11]: https://docs.datadoghq.com/help
