# Redis Integration

# Overview

Whether you use Redis as a database, cache, or message queue, this integration helps you track problems with your Redis servers and the parts of your infrastructure that they serve. The Datadog Agent's Redis check collects a wealth of metrics related to performance, memory usage, blocked clients, slave connections, disk persistence, expired and evicted keys, and many more.

# Installation

The Redis check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Redis servers. If you need the newest version of the check, install the `dd-check-redis` package.

# Configuration

Create a `redisdb.yaml` in the Datadog Agent's `conf.d` directory:

```
init_config:

instances:
  - host: localhost
    port: 6379 # or wherever your redis listens
    # if your redis uses a unix domain socket instead of TCP
    #unix_socket_path: /var/run/redis/redis.sock
    # if your redis requires auth
    #password: myredispassword
```

See [this sample redisdb.yaml](https://github.com/Datadog/integrations-core/blob/master/redisdb/conf.yaml.example) for all available configuration options.

Restart the Agent to begin sending Redis metrics to Datadog.

# Validation

Run the Agent's `info` subcommand and look for `redis` under the Checks section:

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

# Troubleshooting

## Agent cannot connect
```
    redisdb
    -------
      - instance #0 [ERROR]: 'Error 111 connecting to localhost:6379. Connection refused.'
      - Collected 0 metrics, 0 events & 1 service chec
```

Check that the connection info in `redisdb.yaml` is correct.

## Agent cannot authenticate
```
    redisdb
    -------
      - instance #0 [ERROR]: 'NOAUTH Authentication required.'
      - Collected 0 metrics, 0 events & 1 service check
```

Configure a `password` in `redisdb.yaml`.

# Compatibility

The redis check is compatible with all major platforms.

# Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/redisdb/metadata.csv) for a list of metrics provided by this integration.

# Service Checks

`redis.can_connect`:

Returns CRITICAL if the Agent cannot connect to Redis to collect metrics, otherwise OK.

# Further Reading

Read our [series of blog posts](https://www.datadoghq.com/blog/how-to-monitor-redis-performance-metrics/) about how to monitor your Redis servers with Datadog.
