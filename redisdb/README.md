# Redis Integration

## Overview

Whether you use Redis as a database, cache, or message queue, this integration helps you track problems with your Redis servers and the parts of your infrastructure that they serve. The Datadog Agent's Redis check collects a wealth of metrics related to performance, memory usage, blocked clients, slave connections, disk persistence, expired and evicted keys, and many more.

## Setup
### Installation

The Redis check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Redis servers. If you need the newest version of the check, install the `dd-check-redis` package.

### Configuration

Create a `redisdb.yaml` in the Datadog Agent's `conf.d` directory. See the [sample redisdb.yaml](https://github.com/DataDog/integrations-core/blob/master/redisdb/conf.yaml.example) for all available configuration options:

```
init_config:

instances:
  - host: localhost
    port: 6379 # or wherever your redis listens
#   unix_socket_path: /var/run/redis/redis.sock # if your redis uses a socket instead of TCP
#   password: myredispassword                   # if your redis requires auth
```

Configuration Options:

* `unix_socket_path` - (Optional) - Can be used instead of `host` and `port`.
* `db`, `password`, and `socket_timeout` - (Optional) - Additional connection options.
* `warn_on_missing_keys` - (Optional) - Display a warning in the info page if the keys we're tracking are missing.
* `slowlog-max-len` - (Optional) - Maximum number of entries to fetch from the slow query log. By default, the check will
        read this value from the redis config. If it's above 128, it will default to 128 due to potential increased latency
        to retrieve more than 128 slowlog entries every 15 seconds. If you need to get more entries from the slow query logs
        set the value here. Warning: It may impact the performance of your redis instance
* `command_stats` - (Optional) - Collect INFO COMMANDSTATS output as metrics.

See [this sample redisdb.yaml](https://github.com/Datadog/integrations-core/blob/master/redisdb/conf.yaml.example) for all available configuration options.

[Restart the Agent](https://help.datadoghq.com/hc/en-us/articles/203764515-Start-Stop-Restart-the-Datadog-Agent) to begin sending Redis metrics to Datadog.

### Validation

[Run the Agent's `info` subcommand](https://help.datadoghq.com/hc/en-us/articles/203764635-Agent-Status-and-Information) and look for `redisdb` under the Checks section:

```
  Checks
  ======
    [...]

    redisdb
    -------
      - instance #0 [OK]
      - Collected 26 metrics, 0 events & 1 service check

    [...]
```

## Compatibility

The redis check is compatible with all major platforms.

## Data Collected
### Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/redisdb/metadata.csv) for a list of metrics provided by this integration.

### Events
The RedisDB check does not include any event at this time.

### Service Checks

`redis.can_connect`:

Returns CRITICAL if the Agent cannot connect to Redis to collect metrics, otherwise OK.

## Troubleshooting
### Agent cannot connect
```
    redisdb
    -------
      - instance #0 [ERROR]: 'Error 111 connecting to localhost:6379. Connection refused.'
      - Collected 0 metrics, 0 events & 1 service chec
```

Check that the connection info in `redisdb.yaml` is correct.

### Agent cannot authenticate
```
    redisdb
    -------
      - instance #0 [ERROR]: 'NOAUTH Authentication required.'
      - Collected 0 metrics, 0 events & 1 service check
```

Configure a `password` in `redisdb.yaml`.

## Further Reading
Read our [series of blog posts](https://www.datadoghq.com/blog/how-to-monitor-redis-performance-metrics/) about how to monitor your Redis servers with Datadog. We detail the key performance metrics, how to collect them, and how to use Datadog to monitor Redis.