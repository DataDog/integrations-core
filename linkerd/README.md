# Linkerd Integration

## Overview

This check collects distributed system observability metrics from [Linkerd][1].

## Setup
### Installation

The Linkerd check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your server.

### Configuration

Edit the `linkerd.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's directory.
See [sample linkerd.d/conf.yaml][4] for all available configuration options.

### Validation

[Run the Agent's `status` subcommand][5] and look for `linkerd` under the Checks section.

## Data Collected
### Metrics

See [metadata.csv][6] for a list of default metrics provided by this integration.

See [finagle metrics docs][7] for a detailed description of some of the available metrics.
See [this gist][8] for an example of metrics exposed by linkerd.

Attention: Depending on your linkerd configuration, some metrics might not be exposed by linkerd.

To list the metrics exposed by your current configuration, please run
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
Need help? Contact [Datadog Support][9].

## Further Reading
Learn more about infrastructure monitoring and all our integrations on [our blog][10]


[1]: https://linkerd.io/
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/faq/install-core-extra/
[4]: https://github.com/DataDog/integrations-core/blob/master/linkerd/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/linkerd/metadata.csv
[7]: https://twitter.github.io/finagle/guide/Metrics.html
[8]: https://gist.githubusercontent.com/arbll/2f63a5375a4d6d5acface6ca8a51e2ab/raw/bc35ed4f0f4bac7e2643a6009f45f9068f4c1d12/gistfile1.txt
[9]: http://docs.datadoghq.com/help/
[10]: https://www.datadoghq.com/blog/
