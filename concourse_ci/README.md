## Overview

Configure the Datadog Metric Emitter in Concourse CI to:

* Visualize the duration of pipelines, number of containers and mounted volumes of workers.
* Identify slow requests to build routes.

## Setup

### Installation

Concourse CI comes bundled with a Datadog metrics emitter. A prerequisite to configuring [ATC](https://concourse-ci.org/concepts.html) to emit metrics on start is to have a [Datadog Agent](https://app.datadoghq.com/account/settings#agent) installed.

### Configuration

Configure ATC to use the Datadog emitter by setting the following options. It is important to use a prefix of ```concourse.ci``` to avoid emitting [custom metrics](https://docs.datadoghq.com/developers/metrics/custom_metrics/).

### Datadog Metric Emitter Options

See the Concourse CI [documentation](https://concourse-ci.org/metrics.html#configuring-metrics) for more information.
```
Metric Emitter (Datadog):
    --datadog-agent-host=       Datadog agent host to expose dogstatsd metrics [$CONCOURSE_DATADOG_AGENT_HOST]
    --datadog-agent-port=       Datadog agent port to expose dogstatsd metrics [$CONCOURSE_DATADOG_AGENT_PORT]
    --datadog-prefix=           Prefix for all metrics to easily find them in Datadog [$CONCOURSE_DATADOG_PREFIX]
```

## Data Collected

### Metrics,

A list of metrics emitted can be found [here](https://concourse-ci.org/metrics.html).

### Events

This integration does not support events.

### Service

This integration does not collect service checks.

## Troubleshooting

Need help? [Contact Datadog Support](https://docs.datadoghq.com/help/)
