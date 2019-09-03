# Memcache Check

## Overview

The Agent's Memcache check lets you track Memcache's memory use, hits, misses, evictions, fill percent, and much more.

## Setup
### Installation

The Memcache check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your Memcache servers.

### Configuration

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section

#### Host

1. Edit the `mcache.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][3].
  See the [sample mcache.d/conf.yaml][4] for all available configuration options:

    ```yaml
      init_config:

      instances:
        ## @param url - string - required
        ## url used to connect to the Memcached instance.
        #
        - url: localhost
    ```

2. [Restart the Agent][5] to begin sending Memcache metrics to Datadog.

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][1] for guidance on applying the parameters below.

| Parameter            | Value                                 |
|----------------------|---------------------------------------|
| `<INTEGRATION_NAME>` | `memcached`                           |
| `<INIT_CONFIG>`      | blank or `{}`                         |
| `<INSTANCE_CONFIG>`  | `{"url": "%%host%%","port": "11211"}` |

### Validation

[Run the Agent's `status` subcommand][6] and look for `mcache` under the Checks section.

## Data Collected
### Metrics

See [metadata.csv][7] for a list of metrics provided by this check.

The check only collects `memcache.slabs.*` metrics if you set `options.slabs: true` in `mcache.d/conf.yaml`. Likewise, it only collects `memcache.items.*` metrics if you set `options.items: true`.


### Events
The Mcache check does not include any events.

### Service Checks

`memcache.can_connect`:

Returns CRITICAL if the Agent cannot connect to memcache to collect metrics, otherwise OK.

## Troubleshooting
Need help? Contact [Datadog support][8].

## Further Reading

* [Speed up your web applications with Memcached monitoring][9]
* [Instrument Memcached performance metrics with DogStatsD][10]
* [Monitoring ElastiCache performance metrics with Redis or Memcached][11]


[1]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/?tab=agentv6#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/mcache/datadog_checks/mcache/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/mcache/metadata.csv
[8]: https://docs.datadoghq.com/help
[9]: https://www.datadoghq.com/blog/speed-up-web-applications-memcached
[10]: https://www.datadoghq.com/blog/instrument-memcached-performance-metrics-dogstatsd
[11]: https://www.datadoghq.com/blog/monitoring-elasticache-performance-metrics-with-redis-or-memcached
