# KrakenD integration

## Overview

Build a Datadog Agent integration for self-hosted KrakenD API Gateway that scrapes the Prometheus
endpoint of its OpenTelemetry exporter. Use `krakend` as the integration directory. The integration
scrapes one component, the gateway.

Platform teams run KrakenD in front of their services to route, aggregate, and protect API
traffic. They monitor it to see the traffic and latency each route serves, to alert on error rates,
and to find backends that are slow or unreachable.

## What users monitor

### Traffic and errors

- Request rate, duration, and response size the gateway serves, sliced by route and HTTP method.
- Users alert on the 5xx rate across routes, so every metric that carries a status code is also
  sliced by its class (`1xx` to `5xx`), named `status_class`. A status code of `0` means the backend
  never answered and has no class.

### Backends

Request rate, duration, and failures of the calls the gateway makes to each backend, including
timeouts and cancelled calls, so users can find a slow or unreachable backend.

### Dimensions on every metric

- The service name, service version, and deployment environment that the gateway's telemetry
  configuration declares, as `krakend_service_name`, `krakend_service_version`, and
  `krakend_deployment_environment`, so they are not mistaken for unified service tagging.
- Users do not slice by the OpenTelemetry scope (`otel_scope_name`, `otel_scope_version`,
  `otel_scope_schema_url`): it carries the same value on every series.

### Runtime metrics

Users can turn the Go runtime metrics and the process metrics off, each independently, for all
instances or for one instance. Both are on by default. Users know them by the exporter settings that
produce them, so the options are named `go_metrics` and `process_metrics`.

## Enabling the metrics endpoint

The customer configures the gateway; the integration only scrapes it.

- The `telemetry/opentelemetry` component in the gateway configuration, with a Prometheus exporter.
  It serves `/metrics` on port 9090 by default; the port is part of the exporter's configuration.
- `go_metrics` and `process_metrics` enabled on the exporter, for users who want those metrics.
- `service_name`, `service_version`, and `deploy_env` set in the component, for the labels users
  want on every metric.
- The telemetry layers left enabled (the default when `layers` is not declared), so the gateway,
  proxy, backend, and HTTP client metrics are served.

## Design choices

- Default check interval: 15 seconds.
- Installation sizes: typically a few gateway instances with tens of routes and backends; large
  installations have hundreds of routes.
- Auth and TLS: the exporter serves plain HTTP without auth and has no auth or TLS setting.
- Unified service tagging: none.
- Histograms: the Prometheus histograms as they are; users do not need percentiles across gateways.
- Compatibility: no older integration to stay compatible with.

## Versions and scope

- KrakenD Community Edition 3.x, whose configuration file uses format version 4.
- Out of scope: KrakenD Enterprise Edition (it documents the same OpenTelemetry settings, but it is
  not tested); logs and traces; OTLP export, since the integration only scrapes the Prometheus
  exporter.

## Documentation

- [Telemetry and monitoring through
  OpenTelemetry](https://www.krakend.io/docs/telemetry/opentelemetry/)
- [Prometheus metrics endpoint](https://www.krakend.io/docs/telemetry/prometheus/)
- [OpenTelemetry layers and
  metrics](https://www.krakend.io/docs/telemetry/opentelemetry-layers-metrics/)
- [Configuration file structure](https://www.krakend.io/docs/configuration/structure/)
- [Enterprise OpenTelemetry](https://www.krakend.io/docs/enterprise/telemetry/opentelemetry/)
- [krakend-otel 2.0.1 source](https://github.com/krakend/krakend-otel/tree/v2.0.1)
- [krakend-otel 2.0.1 Prometheus
  exporter](https://github.com/krakend/krakend-otel/tree/v2.0.1/exporter/prometheus)
