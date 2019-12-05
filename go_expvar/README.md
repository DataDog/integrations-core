# Go Expvar Integration

![Go graph][1]

## Overview

Track the memory usage of your Go services and collect metrics instrumented from Go's expvar package.

If you prefer to instrument your Go code using only [dogstats-go][2], you can still use this integration to collect memory-related metrics.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The Go Expvar check is packaged with the Agent, so [install the Agent][4] anywhere you run Go services to collect metrics.

### Configuration
#### Prepare your Go service

If your Go service doesn't use the [expvar package][5] already, import it (`import "expvar"`). If you don't want to instrument your own metrics with expvar - i.e. you only want to collect your service's memory metrics - import the package using the blank identifier (`import _ "expvar"`).

If your service doesn't already listen for HTTP requests (with the http package), [make it listen][6] locally just for the Datadog Agent.

#### Connect the Agent

1. Edit the file `go_expvar.d/conf.yaml`, in the `conf.d/` folder at the root of your [Agent's configuration directory][7]. See the [sample go_expvar.d/conf.yaml][8] for all available configuration options.

    ```yaml
        init_config:

        instances:
          - expvar_url: http://localhost:<your_apps_port>
            # optionally change the top-level namespace for metrics, e.g. my_go_app.memstats.alloc
            namespace: my_go_app # defaults to go_expvar, e.g. go_expvar.memstats.alloc
            # optionally define the metrics to collect, e.g. a counter var your service exposes with expvar.NewInt("my_func_counter")

            metrics:
              - path: my_func_counter
                # if you don't want it named my_go_app.my_func_counter
                #alias: my_go_app.preferred_counter_name
                type: count # other valid options: rate, gauge
                #tags:
                #  - "tag_name1:tag_value1"
    ```

    If you don't configure a `metrics` list, the Agent still collects memstat metrics. Use `metrics` to tell the Agent which expvar vars to collect.

2. [Restart the Agent][9] to begin sending memstat and expvar metrics to Datadog.

#### Metrics collection
The Go Expvar integration can potentially emit [custom metrics][10], which may impact your [billing][11]. By default, there is a limit of 350 metrics. If you require additional metrics, contact [Datadog support][12].

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
Need help? Contact [Datadog support][12].

## Further Reading

* [Instrument your Go apps with Expvar and Datadog][15]


[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/go_expvar/images/go_graph.png
[2]: https://github.com/DataDog/datadog-go
[3]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[4]: https://app.datadoghq.com/account/settings#agent
[5]: https://golang.org/pkg/expvar
[6]: https://golang.org/pkg/net/http/#ListenAndServe
[7]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[8]: https://github.com/DataDog/integrations-core/blob/master/go_expvar/datadog_checks/go_expvar/data/conf.yaml.example
[9]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[10]: https://docs.datadoghq.com/developers/metrics/custom_metrics
[11]: https://docs.datadoghq.com/account_management/billing/custom_metrics
[12]: https://docs.datadoghq.com/help
[13]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[14]: https://github.com/DataDog/integrations-core/blob/master/go_expvar/metadata.csv
[15]: https://www.datadoghq.com/blog/instrument-go-apps-expvar-datadog
