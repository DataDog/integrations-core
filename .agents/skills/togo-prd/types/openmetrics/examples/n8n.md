# n8n integration

Build a Datadog Agent integration for self-hosted n8n 2.x, in regular mode and in queue mode, that
scrapes the Prometheus endpoint of its main and worker processes. Use `n8n` as the integration
directory and `n8n` as the metric namespace.

Teams use n8n to automate workflows that connect their services, often running it in queue mode
with separate worker processes. They monitor it to catch failing workflows, to see whether the
queue keeps up with the work, and to know which n8n version each process runs.

## Components and their setup

Main and worker processes serve mostly the same metrics; the queue metrics come only from main
processes. The customer turns the endpoints on with environment variables:

- **Main process**: `N8N_METRICS=true` serves `/metrics` on port 5678.
  `N8N_METRICS_INCLUDE_QUEUE_METRICS=true` adds the queue metrics.
- **Worker processes** (queue mode): `N8N_METRICS=true` and `QUEUE_HEALTH_CHECK_ACTIVE=true` serve
  `/metrics` on the worker server, port 5678 by default (`QUEUE_HEALTH_CHECK_PORT`).
- **Both**: `N8N_METRICS_INCLUDE_WORKFLOW_ID_LABEL=true` for slicing by workflow; the other
  `N8N_METRICS_INCLUDE_*` settings for the optional areas users want, such as
  `N8N_METRICS_INCLUDE_MESSAGE_EVENT_BUS_METRICS`, `N8N_METRICS_INCLUDE_API_ENDPOINTS`, and
  `N8N_METRICS_INCLUDE_CACHE_METRICS`; `N8N_METRICS_INCLUDE_DEFAULT_METRICS` left on (the default)
  for users who want the Node.js and process metrics.

## Use cases

- Workflow executions: how many succeed and fail, and how long they take, sliced by workflow ID, so
  users can alert on a workflow that starts failing or slows down. Not by workflow name: users
  rename workflows, so the name splits series.
- Queue health in queue mode: jobs waiting, active, completed, and failed, so users can alert on a
  queue that grows faster than the workers drain it.
- Workflow and node events (the event bus counters), API endpoint traffic, and cache hits and
  misses, for users who turn them on in n8n. Every other metric the endpoints serve stays in scope.
- The n8n version is on every metric, as `n8n_version`, so users can compare behavior across
  upgrades.
- Node.js runtime and process metrics: off by default, because users monitor the n8n containers or
  hosts with other Agent checks; users can turn them on. When they are on, the Node.js version is
  on them as `nodejs_version`, separate from the n8n version.

## Design choices

- Default check interval: 15 seconds.
- Installation sizes: typically one main process with a few workers and tens of active workflows;
  large installations run many workers and hundreds of active workflows.
- Auth and TLS: the endpoint has no auth or TLS setting of its own; n8n recommends exposing it only
  to internal services.
- Unified service tagging: none.
- Histograms: the Prometheus histograms as they are.
- Compatibility: no older integration to stay compatible with.

## Out of scope

- n8n Cloud: it does not serve the metrics endpoint.
- Logs.
- A metrics prefix other than the default `n8n_` (`N8N_METRICS_PREFIX`).

## Documentation

- [Enable Prometheus
  metrics](https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/configuration-examples/enable-prometheus-metrics)
- [Endpoint environment
  variables](https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/endpoints)
- [Monitor n8n](https://docs.n8n.io/deploy/host-n8n/keep-n8n-running/monitor-n8n)
- [Enable queue mode](https://docs.n8n.io/deploy/host-n8n/configure-n8n/scaling/enable-queue-mode)
- [Queue mode environment
  variables](https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/queue-mode)
- [Prometheus metrics source at
  2.46.4](https://github.com/n8n-io/n8n/tree/n8n@2.46.4/packages/cli/src/metrics/prometheus)
