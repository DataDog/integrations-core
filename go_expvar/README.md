# Go Expvar Integration

## Overview

Track the memory usage of your Go services and collect metrics instrumented from Go's expvar package.

If you prefer to instrument your Go code using only [dogstats-go](https://github.com/DataDog/datadog-go), you can still use this integration to collect memory-related metrics.

## Setup
### Installation

The Go Expvar check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) anywhere you run Go services whose metrics you want to collect.

### Configuration

#### Prepare your Go service

If your Go service doesn't use the [expvar package](https://golang.org/pkg/expvar/) already, you'll need to import it (`import "expvar"`). If you don't want to instrument your own metrics with expvar — i.e. you only want to collect your service's memory metrics — import the package using the blank identifier (`import _ "expvar"`).

If your service doesn't already listen for HTTP requests (via the http package), [make it listen](https://golang.org/pkg/net/http/#ListenAndServe) locally, just for the Datadog Agent.

#### Connect the Agent

Create a file `go_expvar.yaml` in the Agent's `conf.d` directory:

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

Restart the Agent to begin sending memstat and expvar metrics to Datadog.

### Validation

Run the Agent's `info` subcommand and look for `go_expvar` under the Checks section:

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

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/go_expvar/metadata.csv) for a list of metrics provided by this integration.

### Events
The Go-Expvar check does not include any event at this time.

### Service Checks
The Go-Expvar check does not include any service check at this time.

## Troubleshooting

If you have any questions about Datadog or a use case our [Docs](https://docs.datadoghq.com/) didn’t mention, we’d love to help! Here’s how you can reach out to us:

### Visit the Knowledge Base

Learn more about what you can do in Datadog on the [Support Knowledge Base](https://datadog.zendesk.com/agent/).

### Web Support

Messages in the [event stream](https://app.datadoghq.com/event/stream) containing **@support-datadog** will reach our Support Team. This is a convenient channel for referencing graph snapshots or a particular event. In addition, we have a livechat service available during the day (EST) from any page within the app.

### By Email

You can also contact our Support Team via email at [support@datadoghq.com](mailto:support@datadoghq.com).

### Over Slack

Reach out to our team and other Datadog users on [Slack](http://chat.datadoghq.com/).

## Further Reading
### Blog Article
To get a better idea of how (or why) to instrument your Go apps with Expvar and Datadog, check out our [series of blog posts](https://www.datadoghq.com/blog/instrument-go-apps-expvar-datadog/) about it.
