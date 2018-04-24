# Go Expvar Integration
{{< img src="integrations/goexpvar/go_graph.png" alt="Go Graph" responsive="true" popup="true">}}
## Overview

Track the memory usage of your Go services and collect metrics instrumented from Go's expvar package.

If you prefer to instrument your Go code using only [dogstats-go][1], you can still use this integration to collect memory-related metrics.

## Setup
### Installation

The Go Expvar check is packaged with the Agent, so simply [install the Agent][2] anywhere you run Go services whose metrics you want to collect.

### Configuration

#### Prepare your Go service

If your Go service doesn't use the [expvar package][3] already, you'll need to import it (`import "expvar"`). If you don't want to instrument your own metrics with expvar — i.e. you only want to collect your service's memory metrics — import the package using the blank identifier (`import _ "expvar"`).

If your service doesn't already listen for HTTP requests (via the http package), [make it listen][4] locally, just for the Datadog Agent.

#### Connect the Agent

Create a file `go_expvar.yaml` in the Agent's `conf.d` directory. See the [sample go_expvar.yaml][5] for all available configuration options:

```
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
        type: counter # other valid options: rate, gauge
        #tags:
        #  - "tag_name1:tag_value1"
```

If you don't configure a `metrics` list, the Agent will still collect memstat metrics. Use `metrics` to tell the Agent which expvar vars to collect.

[Restart the Agent][6] to begin sending memstat and expvar metrics to Datadog.

### Validation

[Run the Agent's `status` subcommand][7] and look for `go_expvar` under the Checks section:

```
  Checks
  ======
    [...]

    go_expvar
    -------
      - instance #0 [OK]
      - Collected 13 metrics, 0 events & 0 service checks

    [...]
```

## Compatibility

The go_expvar check is compatible with all major platforms.

## Data Collected
### Metrics

See [metadata.csv][8] for a list of metrics provided by this integration.

### Events
The Go-Expvar check does not include any event at this time.

### Service Checks
The Go-Expvar check does not include any service check at this time.

## Troubleshooting
Need help? Contact [Datadog Support][9].

## Further Reading

* [Instrument your Go apps with Expvar and Datadog][10]


[1]: https://github.com/DataDog/datadog-go
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://golang.org/pkg/expvar/
[4]: https://golang.org/pkg/net/http/#ListenAndServe
[5]: https://github.com/DataDog/integrations-core/blob/master/go_expvar/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[7]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/go_expvar/metadata.csv
[9]: http://docs.datadoghq.com/help/
[10]: https://www.datadoghq.com/blog/instrument-go-apps-expvar-datadog/
