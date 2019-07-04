# Memcache Check

## Overview

The Agent's memcache check lets you track memcache's memory use, hits, misses, evictions, fill percent, and much more.

## Setup

Find below instructions to install and configure the check when running the Agent on a host. See the [Autodiscovery Integration Templates documentation][1] to learn how to transpose those instructions in a containerized environment.

### Installation

The memcache check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your memcache servers.

### Configuration

1. Edit the `mcache.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][3].
  See the [sample mcache.d/conf.yaml][4] for all available configuration options:

    ```yaml
      init_config:

      instances:
        - url: localhost  # url used to connect to the memcached instance
          port: 11212 # optional; default is 11211
      #    socket: /path/to/memcache/socket # alternative to url/port; 'dd-agent' user must have read/write permission
          options:
            items: false # set to true to collect items stats
            slabs: false # set to true to collect slabs stats
      #    tags:
      #    - optional_tag
    ```

2. [Restart the Agent][5] to begin sending memcache metrics to Datadog.

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
