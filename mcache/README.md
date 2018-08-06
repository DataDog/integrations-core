# Memcache Check

## Overview

The Agent's memcache check lets you track memcache's memory use, hits, misses, evictions, fill percent, and much more.

## Setup
### Installation

The memcache check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your memcache servers.

### Configuration

1. Edit the `mcache.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][10].
  See the [sample mcache.d/conf.yaml][2] for all available configuration options:

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

2. [Restart the Agent][3] to begin sending memcache metrics to Datadog.

### Validation

[Run the Agent's `status` subcommand][4] and look for `mcache` under the Checks section.

## Data Collected
### Metrics

See [metadata.csv][5] for a list of metrics provided by this check.

The check only collects `memcache.slabs.*` metrics if you set `options.slabs: true` in `mcache.d/conf.yaml`. Likewise, it only collects `memcache.items.*` metrics if you set `options.items: true`.


### Events
The Mcache check does not include any events at this time.

### Service Checks

`memcache.can_connect`:

Returns CRITICAL if the Agent cannot connect to memcache to collect metrics, otherwise OK.

## Troubleshooting
Need help? Contact [Datadog Support][6].

## Further Reading

* [Speed up your web applications with Memcached monitoring][7]
* [Instrument Memcached performance metrics with DogStatsD][8]
* [Monitoring ElastiCache performance metrics with Redis or Memcached][9]


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/mcache/datadog_checks/mcache/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/mcache/metadata.csv
[6]: https://docs.datadoghq.com/help/
[7]: https://www.datadoghq.com/blog/speed-up-web-applications-memcached/
[8]: https://www.datadoghq.com/blog/instrument-memcached-performance-metrics-dogstatsd/
[9]: https://www.datadoghq.com/blog/monitoring-elasticache-performance-metrics-with-redis-or-memcached/
[10]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
