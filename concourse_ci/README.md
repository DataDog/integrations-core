## Overview

Capture metrics emitted by concourse-ci.

## Setup

Concourse-ci comes bundled with a Datadog metrics emitter. Configure the `Datadog Metric Emitter` by
setting the Datadog agent host, port and set the prefix to `concourse.ci.`.

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
