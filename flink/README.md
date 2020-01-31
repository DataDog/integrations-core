# Agent Check: flink

## Overview

This check monitors [flink][1].

## Setup

### Installation

The flink check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. Configure the Datadog HTTP Reporter[3] in Flink.

Copy `/opt/flink-metrics-datadog-1.7.2.jar` into the `/lib` folder.
In the `flink/conf/flink-conf.yaml`, add these lines, replacing xxx with your Datadog API key:

```
metrics.reporter.dghttp.class: org.apache.flink.metrics.datadog.DatadogHttpReporter
metrics.reporter.dghttp.apikey: xxx
metrics.reporter.dghttp.tags: myflinkapp,prod
```

### Validation

<Steps to validate integration is functioning as expected>

## Data Collected

### Metrics

flink does not include any metrics.

### Service Checks

flink does not include any service checks.

### Events

flink does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][1].

[1]: https://docs.datadoghq.com/help
