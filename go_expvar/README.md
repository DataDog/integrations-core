# Go Expvar Integration

![Go graph][1]

## Overview

Track the memory usage of your Go services and collect metrics instrumented from Go's expvar package.

If you prefer to instrument your Go code using only [dogstats-go][2], you can still use this integration to collect memory-related metrics.

## Setup

### Installation

The Go Expvar check is packaged with the Agent, so [install the Agent][3] anywhere you run Go services to collect metrics.

### Configuration

#### Prepare your Go service

If your Go service doesn't use the [expvar package][4] already, import it (`import "expvar"`). If you don't want to instrument your own metrics with expvar - i.e. you only want to collect your service's memory metrics - import the package using the blank identifier (`import _ "expvar"`). If your service doesn't already listen for HTTP requests (with the http package), [make it listen][5] locally just for the Datadog Agent.

#### Host

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

##### Connect the Agent

1. Edit the file `go_expvar.d/conf.yaml`, in the `conf.d/` folder at the root of your [Agent's configuration directory][6]. See the [sample go_expvar.d/conf.yaml][7] for all available configuration options.

    **Note**: If you don't configure a `metrics` list, the Agent still collects memstat metrics. Use `metrics` to tell the Agent which expvar vars to collect.

2. [Restart the Agent][8].

**Note**: The Go Expvar integration can potentially emit [custom metrics][9], which may impact your [billing][10]. By default, there is a limit of 350 metrics. If you require additional metrics, contact [Datadog support][11].

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][12] for guidance on applying the parameters below.

| Parameter            | Value                                    |
| -------------------- | ---------------------------------------- |
| `<INTEGRATION_NAME>` | `go_expvar`                              |
| `<INIT_CONFIG>`      | blank or `{}`                            |
| `<INSTANCE_CONFIG>`  | `{"expvar_url": "http://%%host%%:8080"}` |

### Validation

[Run the Agent's status subcommand][13] and look for `go_expvar` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][14] for a list of metrics provided by this integration.

### Events

The Go-Expvar check does not include any events.

### Service Checks

The Go-Expvar check does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][11].

## Further Reading

- [Instrument your Go apps with Expvar and Datadog][15]

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/go_expvar/images/go_graph.png
[2]: https://github.com/DataDog/datadog-go
[3]: https://app.datadoghq.com/account/settings#agent
[4]: https://golang.org/pkg/expvar
[5]: https://golang.org/pkg/net/http/#ListenAndServe
[6]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[7]: https://github.com/DataDog/integrations-core/blob/master/go_expvar/datadog_checks/go_expvar/data/conf.yaml.example
[8]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[9]: https://docs.datadoghq.com/developers/metrics/custom_metrics
[10]: https://docs.datadoghq.com/account_management/billing/custom_metrics
[11]: https://docs.datadoghq.com/help
[12]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[13]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[14]: https://github.com/DataDog/integrations-core/blob/master/go_expvar/metadata.csv
[15]: https://www.datadoghq.com/blog/instrument-go-apps-expvar-datadog
