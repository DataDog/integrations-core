# Redis Integration

## Overview

Whether you use Redis as a database, cache, or message queue, this integration tracks problems with your Redis servers, cloud service, and the parts of your infrastructure they serve. Use the Datadog Agent's Redis check to collects metrics related to:

- Performance
- Memory usage
- Blocked clients
- Secondary connections
- Disk persistence
- Expired and evicted keys
- and many more

## Setup

### Installation

The Redis check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your Redis servers.

### Configuration

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

##### Metric collection

1. Edit the `redisdb.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][2]. The following parameters may require updating. See the [sample redisdb.d/conf.yaml][3] for all available configuration options.

   ```yaml
   init_config:
   instances:
     ## @param host - string - required
     ## Enter the host to connect to.
     - host: localhost
       ## @param port - integer - required
       ## Enter the port of the host to connect to.
       port: 6379

       ## @param username - string - optional
       ## The username to use for the connection. Redis 6+ only.
       #
       # username: <USERNAME>

       ## @param password - string - optional
       ## The password to use for the connection.
       #
       # password: <PASSWORD>
   ```

2. If using Redis 6+ and ACLs, ensure that the user has at least `DB  Viewer` permissions at the Database level, `Cluster Viewer` permissions if operating in a cluster environment, and `+config|get +info +slowlog|get` ACL rules. For more details, see [Database access control][4].

3. [Restart the Agent][5].

##### Log collection

_Available for Agent versions >6.0_

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
       service: myapplication
   ```

    Change the `path` and `service` parameter values and configure them for your environment. See the [sample redisdb.yaml][3] for all available configuration options.

3. [Restart the Agent][5].

##### Trace collection

Datadog APM integrates with Redis to see the traces across your distributed system. Trace collection is enabled by default in the Datadog Agent v6+. To start collecting traces:

1. [Enable trace collection in Datadog][6].
2. [Instrument your application that makes requests to Redis][7].


<!-- xxz tab xxx -->
<!-- xxx tab "Docker" xxx -->

#### Docker

To configure this check for an Agent running on a container:

##### Metric collection

Set [Autodiscovery Integrations Templates][8] as Docker labels on your application container:

```yaml
LABEL "com.datadoghq.ad.check_names"='["redisdb"]'
LABEL "com.datadoghq.ad.init_configs"='[{}]'
LABEL "com.datadoghq.ad.instances"='[{"host":"%%host%%","port":"6379","password":"%%env_REDIS_PASSWORD%%"}]'
```

**Note**: The `"%%env_<ENV_VAR>%%"` template variable logic is used to avoid storing the password in plain text, hence the `REDIS_PASSWORD` environment variable must be set on the Agent container. See the [Autodiscovery Template Variable][9] documentation for more details. Alternatively, the Agent can leverage the `secrets` package to work with any [secrets management][10] backend (such as HashiCorp Vault or AWS Secrets Manager).

##### Log collection

_Available for Agent versions >6.0_

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Docker Log Collection][11].

Then, set [Log Integrations][12] as Docker labels:

```yaml
LABEL "com.datadoghq.ad.logs"='[{"source":"redis","service":"<YOUR_APP_NAME>"}]'
```

##### Trace collection

APM for containerized apps is supported on Agent v6+ but requires extra configuration to begin collecting traces.

Required environment variables on the Agent container:

| Parameter            | Value                                                                      |
| -------------------- | -------------------------------------------------------------------------- |
| `<DD_API_KEY>` | `api_key`                                                                  |
| `<DD_APM_ENABLED>`      | true                                                              |
| `<DD_APM_NON_LOCAL_TRAFFIC>`  | true |

See [Tracing Docker Applications][13] for a complete list of available environment variables and configuration.

Then, [instrument your application container that makes requests to Redis][7] and set `DD_AGENT_HOST` to the name of your Agent container.


<!-- xxz tab xxx -->
<!-- xxx tab "Kubernetes" xxx -->

#### Kubernetes

To configure this check for an Agent running on Kubernetes:

##### Metric collection

Set [Autodiscovery Integrations Templates][14] as pod annotations on your application container. Aside from this, templates can also be configured using a [file, configmap, or key-value store][15].

**Annotations v1** (for Datadog Agent < v7.36)

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: redis
  annotations:
    ad.datadoghq.com/redis.check_names: '["redisdb"]'
    ad.datadoghq.com/redis.init_configs: '[{}]'
    ad.datadoghq.com/redis.instances: |
      [
        {
          "host": "%%host%%",
          "port":"6379",
          "password":"%%env_REDIS_PASSWORD%%"
        }
      ]
  labels:
    name: redis
spec:
  containers:
    - name: redis
      image: redis:latest
      ports:
        - containerPort: 6379
```

**Annotations v2** (for Datadog Agent v7.36+)

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: redis
  annotations:
    ad.datadoghq.com/redis.checks: |
      {
        "redisdb": {
          "init_config": {},
          "instances": [
            {
              "host": "%%host%%",
              "port":"6379",
              "password":"%%env_REDIS_PASSWORD%%"
            }
          ]
        }
      }
  labels:
    name: redis
spec:
  containers:
    - name: redis
      image: redis:latest
      ports:
        - containerPort: 6379
```

**Note**: The `"%%env_<ENV_VAR>%%"` template variable logic is used to avoid storing the password in plain text, hence the `REDIS_PASSWORD` environment variable must be set on the Agent container. See the [Autodiscovery Template Variable][9] documentation. Alternatively, the Agent can leverage the `secrets` package to work with any [secrets management][10] backend (such as HashiCorp Vault or AWS Secrets Manager).

##### Log collection

_Available for Agent versions >6.0_

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes Log Collection][16].

Then, set [Log Integrations][12] as pod annotations. This can also be configure using a [file, configmap, or key-value store][17].

**Annotations v1/v2**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: redis
  annotations:
    ad.datadoghq.com/redis.logs: '[{"source":"redis","service":"<YOUR_APP_NAME>"}]'
  labels:
    name: redis
spec:
  containers:
    - name: redis
      image: redis:latest
      ports:
        - containerPort: 6379
```

##### Trace collection

APM for containerized apps is supported on hosts running Agent v6+ but requires extra configuration to begin collecting traces.

Required environment variables on the Agent container:

| Parameter            | Value                                                                      |
| -------------------- | -------------------------------------------------------------------------- |
| `<DD_API_KEY>` | `api_key`                                                                  |
| `<DD_APM_ENABLED>`      | true                                                              |
| `<DD_APM_NON_LOCAL_TRAFFIC>`  | true |

See [Tracing Kubernetes Applications][18] and the [Kubernetes Daemon Setup][19] for a complete list of available environment variables and configuration.

Then, [instrument your application container that makes requests to Redis][7].

<!-- xxz tab xxx -->
<!-- xxx tab "ECS" xxx -->

#### ECS

To configure this check for an Agent running on ECS:

##### Metric collection

Set [Autodiscovery Integrations Templates][8] as Docker labels on your application container:

```json
{
  "containerDefinitions": [{
    "name": "redis",
    "image": "redis:latest",
    "dockerLabels": {
      "com.datadoghq.ad.check_names": "[\"redisdb\"]",
      "com.datadoghq.ad.init_configs": "[{}]",
      "com.datadoghq.ad.instances": "[{\"host\":\"%%host%%\",\"port\":\"6379\",\"password\":\"%%env_REDIS_PASSWORD%%\"}]"
    }
  }]
}
```

**Note**: The `"%%env_<ENV_VAR>%%"` template variable logic is used to avoid storing the password in plain text, hence the `REDIS_PASSWORD` environment variable must be set on the Agent container. See the [Autodiscovery Template Variable][9] documentation. Alternatively, the Agent can leverage the `secrets` package to work with any [secrets management][10] backend (such as HashiCorp Vault or AWS Secrets Manager).

##### Log collection

_Available for Agent versions >6.0_

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [ECS Log Collection][20].

Then, set [Log Integrations][12] as Docker labels:

```yaml
{
  "containerDefinitions": [{
    "name": "redis",
    "image": "redis:latest",
    "dockerLabels": {
      "com.datadoghq.ad.logs": "[{\"source\":\"redis\",\"service\":\"<YOUR_APP_NAME>\"}]"
    }
  }]
}
```

##### Trace collection

APM for containerized apps is supported on Agent v6+ but requires extra configuration to begin collecting traces.

Required environment variables on the Agent container:

| Parameter            | Value                                                                      |
| -------------------- | -------------------------------------------------------------------------- |
| `<DD_API_KEY>` | `api_key`                                                                  |
| `<DD_APM_ENABLED>`      | true                                                              |
| `<DD_APM_NON_LOCAL_TRAFFIC>`  | true |

See [Tracing Docker Applications][13] for a complete list of available environment variables and configuration.

Then, [instrument your application container that makes requests to Redis][7] and set `DD_AGENT_HOST` to the [EC2 private IP address][21].

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's status subcommand][22] and look for `redisdb` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][23] for a list of metrics provided by this integration.

### Events

The Redis check does not include any events.

### Service Checks

See [service_checks.json][24] for a list of service checks provided by this integration.

## Troubleshooting

### Agent cannot connect

```shell
    redisdb
    -------
      - instance #0 [ERROR]: 'Error 111 connecting to localhost:6379. Connection refused.'
      - Collected 0 metrics, 0 events & 1 service check
```

Check that the connection info in `redisdb.yaml` is correct.

### Agent cannot authenticate

```shell
    redisdb
    -------
      - instance #0 [ERROR]: 'NOAUTH Authentication required.'
      - Collected 0 metrics, 0 events & 1 service check
```

Configure a `password` in `redisdb.yaml`.

## Further Reading

Additional helpful documentation, links, and articles:

- [How to monitor Redis performance metrics][26]

[1]: https://app.datadoghq.com/account/settings/agent/latest
[2]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[3]: https://github.com/DataDog/integrations-core/blob/master/redisdb/datadog_checks/redisdb/data/conf.yaml.example
[4]: https://docs.redis.com/latest/rs/security/passwords-users-roles/
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/tracing/send_traces/
[7]: https://docs.datadoghq.com/tracing/setup/
[8]: https://docs.datadoghq.com/agent/docker/integrations/?tab=docker
[9]: https://docs.datadoghq.com/agent/faq/template_variables/
[10]: https://docs.datadoghq.com/agent/guide/secrets-management/?tab=linux
[11]: https://docs.datadoghq.com/agent/docker/log/?tab=containerinstallation#installation
[12]: https://docs.datadoghq.com/agent/docker/log/?tab=containerinstallation#log-integrations
[13]: https://docs.datadoghq.com/agent/docker/apm/?tab=linux
[14]: https://docs.datadoghq.com/agent/kubernetes/integrations/?tab=kubernetes
[15]: https://docs.datadoghq.com/agent/kubernetes/integrations/?tab=kubernetes#configuration
[16]: https://docs.datadoghq.com/agent/kubernetes/log/?tab=containerinstallation#setup
[17]: https://docs.datadoghq.com/agent/kubernetes/log/?tab=daemonset#configuration
[18]: https://docs.datadoghq.com/agent/kubernetes/apm/?tab=java
[19]: https://docs.datadoghq.com/agent/kubernetes/daemonset_setup/?tab=k8sfile#apm-and-distributed-tracing
[20]: https://docs.datadoghq.com/agent/amazon_ecs/logs/?tab=linux
[21]: https://docs.datadoghq.com/agent/amazon_ecs/apm/?tab=ec2metadataendpoint#setup
[22]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[23]: https://github.com/DataDog/integrations-core/blob/master/redisdb/metadata.csv
[24]: https://github.com/DataDog/integrations-core/blob/master/redisdb/assets/service_checks.json
[26]: https://www.datadoghq.com/blog/how-to-monitor-redis-performance-metrics
