# Memcache Check

## Overview

The Agent's Memcache check lets you track Memcache's memory use, hits, misses, evictions, fill percent, and much more.

## Setup

### Installation

The Memcache check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your Memcache servers.

### Configuration

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section

When launching the Memcache server, set the binding protocol `-B` to `binary` or `auto`. Automatic (auto) is the default.

#### Metric collection

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

1. Edit the `mcache.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][2]. See the [sample mcache.d/conf.yaml][3] for all available configuration options:

   ```yaml
   init_config:

   instances:
     ## @param url - string - required
     ## url used to connect to the Memcached instance.
     #
     - url: localhost
   ```

2. [Restart the Agent][4] to begin sending Memcache metrics to Datadog.

##### Trace collection

Datadog APM integrates with Memcache to see the traces across your distributed system. Trace collection is enabled by default in the Datadog Agent v6+. To start collecting traces:

1. [Enable trace collection in Datadog][5].
2. [Instrument your application that makes requests to Memcache][6].

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][7] for guidance on applying the parameters below.

| Parameter            | Value                                 |
| -------------------- | ------------------------------------- |
| `<INTEGRATION_NAME>` | `mcache`                              |
| `<INIT_CONFIG>`      | blank or `{}`                         |
| `<INSTANCE_CONFIG>`  | `{"url": "%%host%%","port": "11211"}` |

##### Trace collection

APM for containerized apps is supported on hosts running Agent v6+ but requires extra configuration to begin collecting traces.

Required environment variables on the Agent container:

| Parameter            | Value                                                                      |
| -------------------- | -------------------------------------------------------------------------- |
| `<DD_API_KEY>` | `api_key`                                                                  |
| `<DD_APM_ENABLED>`      | true                                                              |
| `<DD_APM_NON_LOCAL_TRAFFIC>`  | true |

See [Tracing Kubernetes Applications][8] and the [Kubernetes Daemon Setup][9] for a complete list of available environment variables and configuration.

Then, [instrument your application container][6] and set `DD_AGENT_HOST` to the name of your Agent container.

#### Log collection

_Available for Agent versions >6.0_

1. Add this configuration block to your `mcache.d/conf.yaml` file to start collecting your Memcached Logs:

   ```yaml
   logs:
     - type: file
       path: /var/log/memcached.log
       source: memcached
       service: mcache
   ```

    Change the `path` and `service` parameter values and configure them for your environment.

2. [Restart the Agent][4] to validate these changes.

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

Run the [Agent's `status` subcommand][10] and look for `mcache` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][11] for a list of metrics provided by this check.

The check only collects `memcache.slabs.*` metrics if you set `options.slabs: true` in `mcache.d/conf.yaml`. Likewise, it only collects `memcache.items.*` metrics if you set `options.items: true`.

### Events

The Mcache check does not include any events.

### Service Checks

See [service_checks.json][12] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][13].

## Further Reading

- [Speed up your web applications with Memcached monitoring][14]
- [Instrument Memcached performance metrics with DogStatsD][15]
- [Monitoring ElastiCache performance metrics with Redis or Memcached][16]

[1]: https://app.datadoghq.com/account/settings/agent/latest
[2]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[3]: https://github.com/DataDog/integrations-core/blob/master/mcache/datadog_checks/mcache/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/tracing/send_traces/
[6]: https://docs.datadoghq.com/tracing/setup/
[7]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[8]: https://docs.datadoghq.com/agent/kubernetes/apm/?tab=java
[9]: https://docs.datadoghq.com/agent/kubernetes/daemonset_setup/?tab=k8sfile#apm-and-distributed-tracing
[10]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[11]: https://github.com/DataDog/integrations-core/blob/master/mcache/metadata.csv
[12]: https://github.com/DataDog/integrations-core/blob/master/mcache/assets/service_checks.json
[13]: https://docs.datadoghq.com/help/
[14]: https://www.datadoghq.com/blog/speed-up-web-applications-memcached
[15]: https://www.datadoghq.com/blog/instrument-memcached-performance-metrics-dogstatsd
[16]: https://www.datadoghq.com/blog/monitoring-elasticache-performance-metrics-with-redis-or-memcached
