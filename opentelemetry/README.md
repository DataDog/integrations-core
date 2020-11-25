## OpenTelemetry Collector

## Overview

The OpenTelemetry Collector is a vendor-agnostic software that can export telemetry data directly to Datadog servers. 
It can report arbitrary metrics and traces from instrumented applications and general system metrics.

## Setup

### Installation

Please follow the [OpenTelemetry Collector documentation][2] to install the `opentelemetry-collector-contrib` distribution, or any other distribution that includes the Datadog exporter.

The Datadog Agent is **not** needed to export telemetry data to Datadog.

### Configuration

To export telemetry data to Datadog from the OpenTelemetry Collector add the Datadog exporter to your metrics and traces pipelines.
The only required setting is [your API key][3].


A minimal configuration file to retrieve system metrics is as follows.

``` yaml
receivers:
  hostmetrics:
    scrapers:
      load:
      cpu:
      disk:
      filesystem:
      memory:
      network:
      swap:
      process:

processors:
  batch:
    timeout: 10s

exporters:
  datadog:
    api:
      key: "<Your API key goes here>"
      
service:
  pipelines:
    metrics:
      receivers: [hostmetrics]
      processors: [batch]
      exporters: [datadog]
```

For further information on the Datadog exporter settings visit the [Datadog exporter documentation][4].

Note that to instrument your custom applications you will need to add suitable receivers to this configuration.
For more details on how pipelines and different components work, visit the [OpenTelemetry Collector documentation][5].

### Validation

Check the OpenTelemetry Collector logs. You should see the Datadog exporter being enabled and started correctly.

## Data Collected

### Metrics

See [metadata.csv][6] for a list of metrics provided by this check (if using the `hostmetrics` receiver as in the sample configuration above).

Different groups of metrics can be enabled and customized by following the [hostmetrics receiver instructions](https://github.com/open-telemetry/opentelemetry-collector/tree/master/receiver/hostmetricsreceiver).
CPU and disk metrics are not available on macOS.

### Service Checks

The OpenTelemetry Collector does not include any service checks.

### Events

The OpenTelemetry Collector does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][1].

[1]: https://docs.datadoghq.com/help/
[2]: https://opentelemetry.io/docs/collector/getting-started/
[3]: https://app.datadoghq.com/account/settings#api
[4]: https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/master/exporter/datadogexporter/README.md
[5]: https://opentelemetry.io/docs/collector/getting-started/
[6]: https://github.com/DataDog/integrations-core/blob/master/opentelemetry/metadata.csv
