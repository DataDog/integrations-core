# Redis Integration

## Overview

Whether you use Redis as a database, cache, or message queue, this integration helps you track problems with your Redis servers and the parts of your infrastructure that they serve. The Datadog Agent's Redis check collects metrics related to performance, memory usage, blocked clients, slave connections, disk persistence, expired and evicted keys, and many more.

## Setup
### Installation

The Redis check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your Redis servers.

### Configuration
#### Host

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

##### Metric collection

1. Edit the `redisdb.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][3]. The following parameters may require updating. See the [sample redisdb.d/conf.yaml][4] for all available configuration options.

    ```yaml
      init_config:
      instances:
        ## @param host - string - required
        ## Enter the host to connect to.
        - host: localhost
          ## @param port - integer - required
          ## Enter the port of the host to connect to.
          port: 6379
      ```

2. [Restart the Agent][5].

##### Log collection

**Available for Agent >6.0**

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

    ```yaml
      logs_enabled: true
    ```

2. Uncomment and edit this configuration block at the bottom of your `redisdb.d/conf.yaml`:

    ```yaml
      logs:
          - type: file
            path: /var/log/redis_6379.log
            source: redis
            sourcecategory: database
            service: myapplication
    ```

    Change the `path` and `service` parameter values and configure them for your environment. See the [sample redisdb.yaml][4] for all available configuration options.

3. [Restart the Agent][5].

#### Containerized
For containerized environments, see the [Autodiscovery Integration Templates][1] for guidance on applying the parameters below.

##### Metric collection

| Parameter            | Value                                                                                       |
|----------------------|---------------------------------------------------------------------------------------------|
| `<INTEGRATION_NAME>` | `redisdb`                                                                                   |
| `<INIT_CONFIG>`      | blank or `{}`                                                                               |
| `<INSTANCE_CONFIG>`  | <pre>{"host": "%%host%%",<br> "port":"6379",<br> "password":"%%env_REDIS_PASSWORD%%"}</pre> |

##### Log collection

**Available for Agent v6.5+**

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Docker log collection][11].

| Parameter      | Value                                               |
|----------------|-----------------------------------------------------|
| `<LOG_CONFIG>` | `{"source": "redis", "service": "<YOUR_APP_NAME>"}` |

### Validation

[Run the Agent's status subcommand][6] and look for `redisdb` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The Redis check does not include any events.

### Service Checks

**redis.can_connect**:<br>
Returns `CRITICAL` if the Agent cannot connect to Redis to collect metrics, otherwise returns `OK`.

**redis.replication.master_link_status**:<br>
Returns `CRITICAL` if this Redis instance is unable to connect to its master instance, otherwise returns `OK`.

## Troubleshooting

* [Redis Integration Error: "unknown command 'CONFIG'"][8]

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

Additional helpful documentation, links, and articles:

* [How to monitor Redis performance metrics][10]


[1]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/redisdb/datadog_checks/redisdb/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/redisdb/metadata.csv
[8]: https://docs.datadoghq.com/integrations/faq/redis-integration-error-unknown-command-config
[9]: https://docs.datadoghq.com/developers/integrations
[10]: https://www.datadoghq.com/blog/how-to-monitor-redis-performance-metrics
[11]: https://docs.datadoghq.com/agent/docker/log/?tab=containerinstallation#setup
