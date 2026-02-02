# Agent Check: KrakenD

## Overview

This check monitors [KrakenD][1] through the Datadog Agent.

KrakenD is a high-performance API Gateway that provides a single entry point for microservices. This integration collects metrics using KrakenD's [OpenTelemetry exporter with Prometheus format][2] and supports [log collection][3] for comprehensive monitoring.

### What This Integration Monitors

The integration collects metrics across multiple [layers][4] of the KrakenD gateway:

- **HTTP Server Layer**: Request durations, response sizes, and status codes for client-facing traffic
- **Proxy Layer**: Processing times and performance metrics for KrakenD's internal proxy operations
- **Backend Layer**: Connection times, response durations, error rates, DNS resolution, TLS handshakes, timeouts, and connection details for upstream service calls
- **Go Runtime**: Garbage collection, memory usage, goroutines, and Go-specific performance metrics
- **System Process**: CPU usage, memory consumption, file descriptors, and network I/O

In addition to metrics, you can collect access and application logs from KrakenD.

### Deployment Support

This integration works with KrakenD in both containerized (Docker, Kubernetes) and traditional deployment environments.


## Setup

### Installation

The KrakenD check is included in the [Datadog Agent][6] package. No additional installation is needed on your server.

### Configuration

### Metrics

The KrakenD integration uses the OpenTelemetry component in KrakenD with a Prometheus exporter to parse and emit metrics to Datadog. Make sure that your KrakenD installation is configured appropriately following the [instructions provided by KrakenD][7] and use the `prometheus` exporter.

The snippet below configures KrakenD to emit metrics for [all layers][4] including Go and process metrics, exposing the Prometheus metrics endpoint on port 9090 on all network interfaces (`0.0.0.0`). The specific endpoint URL you configure in the integration as the `openmetrics_endpoint` option depends on your deployment:

- **Same host**: `http://localhost:9090/metrics`
- **Docker containers and Kubernetes**: With Autodiscovery you can use the template variable `%%host%%`: `http://%%host%%:9090/metrics`.

```json
{
   "extra_config": {
      "telemetry/opentelemetry": {
         "service_name": "krakend-gateway",
         "service_version": "1.0.0",
         "exporters": {
               "prometheus": [
                  {
                     "name": "krakend_metrics",
                     "port": 9090,
                     "listen_ip": "0.0.0.0",
                     "process_metrics": true,
                     "go_metrics": true
                  }
               ]
         },
         "layers": {
               "global": {
                  "disable_metrics": false
               },
               "proxy": {
                  "disable_metrics": false
               },
               "backend": {
                  "metrics": {
                     "disable_stage": false,
                     "round_trip": true,
                     "read_payload": true,
                     "detailed_connection": true,
                     "static_attributes": [
                           {
                              "key": "backend_type",
                              "value": "test_api"
                           }
                     ]
                  }
               }
         }
      }
   }
}
```

In KrakenD, emitting Go and process metrics is optional and can be disabled by setting `go_metrics` and `process_metrics` to `false`. For debugging purposes, to emit these metrics but not send them to Datadog, you can set the same options to `false` in the integration configuration. By default, they are enabled to respect the configuration set up in KrakenD.

To configure the integration with KrakenD deployed on a host:

1. Edit the `krakend.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your KrakenD performance data. See the sample [`krakend.d/conf.yaml`][9] for all available configuration options.

2. [Restart the Agent][10].

For containerized environments, see the [Autodiscovery Integration Templates][5] for guidance.

### Logs

Ensure the agent is configured to load logs following the instructions about [Log Collection and Integrations][3].

To enable collection of KrakenD access and application logs, uncomment this section in the integration configuration file, replacing `<SERVICE>`  with the service to associate the logs with:

```yaml
logs:
  - type: docker
    source: krakend
    service: <SERVICE>
```

Alternatively, in containerized environments, you can use Autodiscovery (for example, see [Docker][11] or [Kubernetes][12]) to add the logs configuration through annotations to the container or node where KrakenD is running.
### Validation

[Run the Agent's status subcommand][13] and look for `krakend` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][14] for a list of metrics provided by this integration.

### Events

The KrakenD integration does not include any events.

### Service Checks

See [service_checks.json][15] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][16].


[1]: https://www.krakend.io/
[2]: https://www.krakend.io/docs/telemetry/prometheus/
[3]: https://docs.datadoghq.com/logs/log_collection/
[4]: https://www.krakend.io/docs/telemetry/opentelemetry-layers-metrics/
[5]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[6]: https://app.datadoghq.com/account/settings/agent/latest
[7]: https://www.krakend.io/docs/telemetry/opentelemetry/
[8]: https://www.krakend.io/docs/telemetry/opentelemetry-layers-metrics/
[9]: https://github.com/DataDog/integrations-core/blob/master/krakend/datadog_checks/krakend/data/conf.yaml.example
[10]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[11]: https://docs.datadoghq.com/containers/docker/log
[12]: https://docs.datadoghq.com/containers/kubernetes/log/
[13]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[14]: https://github.com/DataDog/integrations-core/blob/master/krakend/metadata.csv
[15]: https://github.com/DataDog/integrations-core/blob/master/krakend/assets/service_checks.json
[16]: https://docs.datadoghq.com/help/