# Agent Check: Datadog Agent

## Overview

This check monitors the [Datadog Agent][1] itself by scraping the internal telemetry it exposes in the OpenMetrics format. Use it to track the health and throughput of the Agent's core components, such as the forwarder, DogStatsD, the aggregator, the check scheduler, and the Logs Agent.

This integration replaces the deprecated [Agent Metrics][2] integration, which collects similar data through the `go_expvar` check. Compared to the expvar endpoint, the telemetry endpoint provides typed metrics, more granular tags, and a larger set of available metrics.

**Note:** The Agent's internal telemetry might change between minor Agent versions. Such changes might not be mentioned in the Agent's changelog.

## Setup

### Installation

The Datadog Agent check is included in the [Datadog Agent][3] package. No additional installation is needed.

Some default metrics require Agent v7.86.0 or later. Earlier Agent versions report only part of the default set.

### Configuration

The Agent always serves its telemetry at `/telemetry` on the port set by `expvar_port` in [`datadog.yaml`][4], which defaults to `5000`. This check does not require `telemetry.enabled: true`. That setting only enables additional telemetry.

1. Edit the `datadog_agent.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][4]. See the [sample datadog_agent.d/conf.yaml][5] for all available configuration options. For example:

   ```yaml
   init_config:

   instances:
     - openmetrics_endpoint: http://localhost:5000/telemetry
   ```

   To collect telemetry beyond the default set, list the metrics to add with the `extra_metrics` option. You can view all available metrics by querying the `/telemetry` endpoint directly.

2. [Restart the Agent][6].

### Validation

[Run the Agent's status subcommand][7] and look for `datadog_agent` under the Checks section.

### Migrating from Agent Metrics

The Datadog Agent integration collects similar data to the [Agent Metrics][2] integration, but most metric names, types, and tags differ. You must update any dashboards and monitors that query metrics from the Agent Metrics integration.

1. Configure the Datadog Agent integration as described in [Configuration](#configuration).
2. Optionally, keep `go_expvar.d/agent_stats.yaml` in place while you update your dashboards and monitors, so that you can compare the old and new metrics. Three metrics have the same name in both integrations: `datadog.agent.aggregator.dogstatsd_contexts`, `datadog.agent.forwarder.transactions.retry_queue_size`, and `datadog.agent.scheduler.checks_entered`. While both checks run, each check submits these metrics.
3. Update your dashboards and monitors using the [metric mapping](#metric-mapping).
4. Remove `go_expvar.d/agent_stats.yaml` and [restart the Agent][6].

#### Behavior changes

- **Counters are submitted as counts.** Agent Metrics submitted counters as per-second rates. The Datadog Agent integration submits them as counts with a `.count` suffix. For example, to get the equivalent of `datadog.agent.forwarder.transactions.success`, query `datadog.agent.forwarder.transactions.success.count` with the `.as_rate()` function.
- **Related metrics are combined and distinguished by tags.** For example, `datadog.agent.dogstatsd.processed.count`, tagged by `message_type` and `state`, replaces the separate DogStatsD packet and parse error metrics.
- **Some metrics are now under the `datadog.agent.` namespace.** Agent Metrics submitted `scheduler.queues.size`, `scheduler.queues.interval`, `batch_strategy.idle_time`, and `batch_strategy.in_use_time` without a namespace.
- **Go runtime metrics are not collected by default.** Agent Metrics also collected Go memory statistics, such as `datadog.agent.memstats.heap_alloc`. The telemetry endpoint exposes them as `go_memstats_*` and `go_gc_*` metrics. To collect them, use the `extra_metrics` option. For example:

  ```yaml
  instances:
    - openmetrics_endpoint: http://localhost:5000/telemetry
      extra_metrics:
        - go_memstats_heap_alloc_bytes: go.memstats.heap_alloc
        - go_memstats_heap_inuse_bytes: go.memstats.heap_inuse
  ```

#### Metric mapping

Unless noted otherwise, all metric names in the table are prefixed with `datadog.agent.`.

| Agent Metrics metric | Datadog Agent metric |
| --- | --- |
| `forwarder.transactions.success` | `forwarder.transactions.success.count` |
| `forwarder.transactions.errors` | `forwarder.transactions.errors.count` |
| `forwarder.transactions.errors_by_type.dns_errors` | `forwarder.transactions.errors.count` with `error_type:dns_lookup_failure` |
| `forwarder.transactions.errors_by_type.tls_errors` | `forwarder.transactions.errors.count` with `error_type:tls_handshake_failure` |
| `forwarder.transactions.errors_by_type.connection_errors` | `forwarder.transactions.errors.count` with `error_type:connection_failure` |
| `forwarder.transactions.errors_by_type.wrote_request_errors` | `forwarder.transactions.errors.count` with `error_type:writing_failure` |
| `forwarder.transactions.errors_by_type.sent_request_errors` | `forwarder.transactions.errors.count` with `error_type:invalid_request` |
| `forwarder.transactions.http_errors` | `forwarder.transactions.http_errors.count`, tagged by `code` |
| `forwarder.transactions.retry_queue_size` | `forwarder.transactions.retry_queue_size`, tagged by `domain` |
| `forwarder.transactions.dropped_on_input` | No longer reported by the Agent. See `forwarder.transactions.dropped.count`. |
| `dogstatsd.metric_packets` | `dogstatsd.processed.count` with `message_type:metrics` and `state:ok` |
| `dogstatsd.metric_parse_errors` | `dogstatsd.processed.count` with `message_type:metrics` and `state:error` |
| `dogstatsd.event_packets` | `dogstatsd.processed.count` with `message_type:events` and `state:ok` |
| `dogstatsd.event_parse_errors` | `dogstatsd.processed.count` with `message_type:events` and `state:error` |
| `dogstatsd.service_check_packets` | `dogstatsd.processed.count` with `message_type:service_checks` and `state:ok` |
| `dogstatsd.service_check_parse_errors` | `dogstatsd.processed.count` with `message_type:service_checks` and `state:error` |
| `dogstatsd_udp.packets` | `dogstatsd_udp.packets.count` with `state:ok` |
| `dogstatsd_udp.packet_reading_errors` | `dogstatsd_udp.packets.count` with `state:error` |
| `dogstatsd_uds.packets` | `dogstatsd_uds.packets.count` with `state:ok` |
| `dogstatsd_uds.packet_reading_errors` | `dogstatsd_uds.packets.count` with `state:error` |
| `dogstatsd_uds.origin_detection_errors` | `dogstatsd_uds.origin_detection_errors.count` |
| `aggregator.dogstatsd_contexts` | `aggregator.dogstatsd_contexts`, tagged by `shard` |
| `aggregator.series_flushed` | `aggregator.flush.count` with `data_type:series` |
| `aggregator.service_check_flushed` | `aggregator.flush.count` with `data_type:service_checks` |
| `aggregator.events_flushed` | `aggregator.flush.count` with `data_type:events` |
| `aggregator.checks_metric_sample` | `aggregator.processed.count` with `data_type:metrics` |
| `aggregator.dogstatsd_metric_sample` | `aggregator.processed.count` with `data_type:dogstatsd_metrics` |
| `aggregator.service_check` | `aggregator.processed.count` with `data_type:service_checks` |
| `aggregator.event` | `aggregator.processed.count` with `data_type:events` |
| `aggregator.number_of_flush` | `aggregator.number_of_flush.count` |
| `aggregator.flush.main_flush_time.last_flush` | `aggregator.flush_time` with `flush_type:main` |
| `aggregator.flush.checks_metric_sample_flush_time.last_flush` | `aggregator.flush_time` with `flush_type:checks_metric_sample` |
| `aggregator.flush.service_check_flush_time.last_flush` | `aggregator.flush_time` with `flush_type:service_check` |
| `aggregator.flush.event_flush_time.last_flush` | `aggregator.flush_time` with `flush_type:event` |
| `aggregator.flush.metric_sketch_flush_time.last_flush` | `aggregator.flush_time` with `flush_type:metric_sketch` |
| `aggregator.flush_count.series.last_flush` | `aggregator.flush_count` with `flush_type:series` |
| `aggregator.flush_count.service_checks.last_flush` | `aggregator.flush_count` with `flush_type:service_checks` |
| `aggregator.flush_count.events.last_flush` | `aggregator.flush_count` with `flush_type:events` |
| `aggregator.flush_count.sketches.last_flush` | `aggregator.flush_count` with `flush_type:sketches` |
| `aggregator.hostname_update` | No longer reported by the Agent. |
| `scheduler.checks_entered` | `scheduler.checks_entered`, tagged by `check_name` |
| `scheduler.queues_count` | `scheduler.queues_count.count` |
| `scheduler.queues.size` (no namespace) | `scheduler.queues.size`, tagged by `interval` |
| `scheduler.queues.interval` (no namespace) | No equivalent. Use the `interval` tag of `scheduler.queues.size`. |
| `splitter.*` | No longer reported by the Agent. |
| `logs_agent.logs_decoded` | `logs_agent.logs_decoded.count` |
| `logs_agent.logs_processed` | `logs_agent.logs_processed.count` |
| `logs_agent.logs_sent` | `logs_agent.logs_sent.count` |
| `logs_agent.bytes_sent` | `logs_agent.bytes_sent.count` |
| `logs_agent.encoded_bytes_sent` | `logs_agent.encoded_bytes_sent.count` |
| `logs_agent.destination_errors` | `logs_agent.destination_errors.count` |
| `logs_agent.is_running` | Not collected. |
| `batch_strategy.idle_time` (no namespace) | `batch_strategy.idle_time.count`, tagged by `sender` (for example, `sender:logs_0_reliable_0` instead of `sender:0`) |
| `batch_strategy.in_use_time` (no namespace) | `batch_strategy.in_use_time.count`, tagged by `sender` |
| `memstats.*` | Not collected by default. See the `extra_metrics` example in [Behavior changes](#behavior-changes). |

## Data Collected

### Metrics

See [metadata.csv][8] for a list of metrics provided by this integration.

### Events

The Datadog Agent integration does not include any events.

### Service Checks

See [service_checks.json][9] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][10].

[1]: https://docs.datadoghq.com/agent/
[2]: https://docs.datadoghq.com/integrations/agent_metrics/
[3]: /account/settings/agent/latest
[4]: https://docs.datadoghq.com/agent/configuration/agent-configuration-files/
[5]: https://github.com/DataDog/integrations-core/blob/master/datadog_agent/datadog_checks/datadog_agent/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/configuration/agent-commands/#start-stop-and-restart-the-agent
[7]: https://docs.datadoghq.com/agent/configuration/agent-commands/#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/datadog_agent/metadata.csv
[9]: https://github.com/DataDog/integrations-core/blob/master/datadog_agent/assets/service_checks.json
[10]: https://docs.datadoghq.com/help/
