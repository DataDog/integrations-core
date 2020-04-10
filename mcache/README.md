# Memcache Check

## Overview

The Agent's Memcache check lets you track Memcache's memory use, hits, misses, evictions, fill percent, and much more.

## Setup

### Installation

The Memcache check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your Memcache servers.

### Configuration

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section

#### Metric Collection

##### Host

1. Edit the `mcache.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][3]. See the [sample mcache.d/conf.yaml][4] for all available configuration options:

   ```yaml
   init_config:

   instances:
     ## @param url - string - required
     ## url used to connect to the Memcached instance.
     #
     - url: localhost
   ```

2. [Restart the Agent][5] to begin sending Memcache metrics to Datadog.

##### Trace collection

Datadog APM integrates with Memcache to see the traces across your distributed system. Trace collection is enabled by default in the Datadog Agent v6+. To start collecting traces:

1. [Enable trace collection in Datadog][6].
2. [Instrument your application that makes requests to Memchache][7].

##### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][1] for guidance on applying the parameters below.

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

See [Tracing Kubernetes Applications][14] and the [Kubernetes Daemon Setup][15] for a complete list of available environment variables and configuration.

Then, [instrument your application container][7] and set `DD_AGENT_HOST` to the name of your Agent container.

#### Log Collection

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

2. [Restart the Agent][5] to validate these changes.

### Validation

[Run the Agent's `status` subcommand][8] and look for `mcache` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][9] for a list of metrics provided by this check.

The check only collects `memcache.slabs.*` metrics if you set `options.slabs: true` in `mcache.d/conf.yaml`. Likewise, it only collects `memcache.items.*` metrics if you set `options.items: true`.

### Events

The Mcache check does not include any events.

### Service Checks

`memcache.can_connect`:

Returns `CRITICAL` if the Agent cannot connect to memcache to collect metrics, otherwise `OK`.

## Troubleshooting

Need help? Contact [Datadog support][10].

## Further Reading

- [Speed up your web applications with Memcached monitoring][11]
- [Instrument Memcached performance metrics with DogStatsD][12]
- [Monitoring ElastiCache performance metrics with Redis or Memcached][13]

[1]: https://docs.datadoghq.com/agent/kubernetes/integrations
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/mcache/datadog_checks/mcache/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/tracing/send_traces/
[7]: https://docs.datadoghq.com/tracing/setup/
[8]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[9]: https://github.com/DataDog/integrations-core/blob/master/mcache/metadata.csv
[10]: https://docs.datadoghq.com/help
[11]: https://www.datadoghq.com/blog/speed-up-web-applications-memcached
[12]: https://www.datadoghq.com/blog/instrument-memcached-performance-metrics-dogstatsd
[13]: https://www.datadoghq.com/blog/monitoring-elasticache-performance-metrics-with-redis-or-memcached
[14]: https://docs.datadoghq.com/agent/kubernetes/apm/?tab=java
[15]: https://docs.datadoghq.com/agent/kubernetes/daemonset_setup/?tab=k8sfile#apm-and-distributed-tracing
