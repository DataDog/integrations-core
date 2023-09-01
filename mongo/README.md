# MongoDB check

![MongoDB Dashboard][1]

## Overview

Connect MongoDB to Datadog in order to:

- Visualize key MongoDB metrics.
- Correlate MongoDB performance with the rest of your applications.

You can also create your own metrics using custom `find`, `count` and `aggregate` queries.

**Note**: MongoDB v3.0+ is required for this integration. Integration of MongoDB Atlas with Datadog is only available on M10+ clusters.

## Setup

### Installation

The MongoDB check is included in the [Datadog Agent][2] package. No additional installation is necessary.

### Architecture

Most low-level metrics (uptime, storage size etc.) needs to be collected on every mongod node. Other higher-level metrics (collection/index statistics etc.) should be collected only once. For these reasons the way you configure the Agents depends on how your mongo cluster is deployed.

<!-- xxx tabs xxx -->
<!-- xxx tab "Standalone" xxx -->
#### Standalone

To configure this integration for a single node MongoDB deployment:

##### Prepare MongoDB
In a Mongo shell, create a read-only user for the Datadog Agent in the `admin` database:

```shell
# Authenticate as the admin user.
use admin
db.auth("admin", "<YOUR_MONGODB_ADMIN_PASSWORD>")

# Create the user for the Datadog Agent.
db.createUser({
  "user": "datadog",
  "pwd": "<UNIQUEPASSWORD>",
  "roles": [
    { role: "read", db: "admin" },
    { role: "clusterMonitor", db: "admin" },
    { role: "read", db: "local" }
  ]
})
```

##### Configure the agents
You only need a single agent, preferably running on the same node, to collect all the available mongo metrics. See below for configuration options.
<!-- xxz tab xxx -->
<!-- xxx tab "Replica Set" xxx -->
#### Replica set

To configure this integration for a MongoDB replica set:

##### Prepare MongoDB
In a Mongo shell, authenticate to the primary and create a read-only user for the Datadog Agent in the `admin` database:

```shell
# Authenticate as the admin user.
use admin
db.auth("admin", "<YOUR_MONGODB_ADMIN_PASSWORD>")

# Create the user for the Datadog Agent.
db.createUser({
  "user": "datadog",
  "pwd": "<UNIQUEPASSWORD>",
  "roles": [
    { role: "read", db: "admin" },
    { role: "clusterMonitor", db: "admin" },
    { role: "read", db: "local" }
  ]
})
```

##### Configure the agents

Install the Datadog Agent on each host in the MongoDB replica set and configure the Agent to connect to the replica on that host (`localhost`). Running an Agent on each host results in lower latency and execution times, and ensures that data is still connected in the event a host fails.

For example, on the primary node:

```yaml
init_config:
instances:
  - hosts:
      - mongo-primary:27017
```

On the secondary node:

```yaml
init_config:
instances:
  - hosts:
      - mongo-secondary:27017
```

On the tertiary node:

```yaml
init_config:
instances:
  - hosts:
      - mongo-tertiary:27017
```

<!-- xxz tab xxx -->
<!-- xxx tab "Sharding" xxx -->
#### Sharding

To configure this integration for a MongoDB sharded cluster:

##### Prepare MongoDB
For each shard in your cluster, connect to the primary of the replica set and create a local read-only user for the Datadog Agent in the `admin` database:

```shell
# Authenticate as the admin user.
use admin
db.auth("admin", "<YOUR_MONGODB_ADMIN_PASSWORD>")

# Create the user for the Datadog Agent.
db.createUser({
  "user": "datadog",
  "pwd": "<UNIQUEPASSWORD>",
  "roles": [
    { role: "read", db: "admin" },
    { role: "clusterMonitor", db: "admin" },
    { role: "read", db: "local" }
  ]
})
```

Then create the same user from a mongos proxy. This action creates the local user in the config servers and allows direct connection.

##### Configure the Agents
1. Configure one Agent for each member of each shard.
2. Configure one Agent for each member of the config servers.
3. Configure one extra Agent to connect to the cluster through a mongos proxy. This mongos proxy can be a new one dedicated to monitoring purposes, or an existing mongos proxy.

**Note**: Monitoring of arbiter nodes is not supported (see the [MongoDB Replica Set Arbiter][3] for more details). However, any status change of an arbiter node is reported by the Agent connected to the primary.

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->


### Configuration

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Docker](?tab=docker#docker), [Kubernetes](?tab=kubernetes#kubernetes), or [ECS](?tab=ecs#ecs) sections.

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

##### Metric collection

1. Edit the `mongo.d/conf.yaml` file in the `conf.d` folder at the root of your [Agent's configuration directory][4]. See the [sample mongo.d/conf.yaml][5] for all available configuration options.

   ```yaml
   init_config:

   instances:
       ## @param hosts - list of strings - required
       ## Hosts to collect metrics from, as is appropriate for your deployment topology.
       ## E.g. for a standalone deployment, specify the hostname and port of the mongod instance.
       ## For replica sets or sharded clusters, see instructions in the sample conf.yaml.
       ## Only specify multiple hosts when connecting through mongos
       #
     - hosts:
         - <HOST>:<PORT>

       ## @param username - string - optional
       ## The username to use for authentication.
       #
       username: datadog

       ## @param password - string - optional
       ## The password to use for authentication.
       #
       password: <UNIQUEPASSWORD>

       ## @param database - string - optional
       ## The database to collect metrics from.
       #
       database: <DATABASE>

       ## @param options - mapping - optional
       ## Connection options. For a complete list, see:
       ## https://docs.mongodb.com/manual/reference/connection-string/#connections-connection-options
       #
       options:
         authSource: admin
   ```

2. [Restart the Agent][6].

##### Trace collection

Datadog APM integrates with Mongo to see the traces across your distributed system. Trace collection is enabled by default in the Datadog Agent v6+. To start collecting traces:

1. [Enable trace collection in Datadog][7].
2. [Instrument your application that makes requests to Mongo][8].

##### Log collection

_Available for Agent versions >6.0_

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

2. Add this configuration block to your `mongo.d/conf.yaml` file to start collecting your MongoDB logs:

   ```yaml
   logs:
     - type: file
       path: /var/log/mongodb/mongodb.log
       service: mongo
       source: mongodb
   ```

    Change the `service` and `path` parameter values and configure them for your environment. See the [sample mongo.yaml][5] for all available configuration options

3. [Restart the Agent][6].

<!-- xxz tab xxx -->
<!-- xxx tab "Docker" xxx -->

#### Docker

To configure this check for an Agent running on a container:

##### Metric collection

Set [Autodiscovery Integrations Templates][9] as Docker labels on your application container:

```yaml
LABEL "com.datadoghq.ad.check_names"='["mongo"]'
LABEL "com.datadoghq.ad.init_configs"='[{}]'
LABEL "com.datadoghq.ad.instances"='[{"hosts": ["%%host%%:%%port%%"], "username": "datadog", "password" : "<UNIQUEPASSWORD>", "database": "<DATABASE>"}]'
```

##### Log collection

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Docker Log Collection][10].

Then, set [Log Integrations][11] as Docker labels:

```yaml
LABEL "com.datadoghq.ad.logs"='[{"source":"mongodb","service":"<SERVICE_NAME>"}]'
```

##### Trace collection

APM for containerized apps is supported on Agent v6+ but requires extra configuration to begin collecting traces.

Required environment variables on the Agent container:

| Parameter            | Value                                                                      |
| -------------------- | -------------------------------------------------------------------------- |
| `<DD_API_KEY>` | `api_key`                                                                  |
| `<DD_APM_ENABLED>`      | true                                                              |
| `<DD_APM_NON_LOCAL_TRAFFIC>`  | true |

See [Tracing Docker Applications][12] for a complete list of available environment variables and configuration.

Then, [instrument your application container][8] and set `DD_AGENT_HOST` to the name of your Agent container.


<!-- xxz tab xxx -->
<!-- xxx tab "Kubernetes" xxx -->

#### Kubernetes

To configure this check for an Agent running on Kubernetes:

##### Metric collection

Set [Autodiscovery Integrations Templates][13] as pod annotations on your application container. Aside from this, templates can also be configure with a [file, configmap, or key-value store][14].

**Annotations v1** (for Datadog Agent < v7.36)

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: mongo
  annotations:
    ad.datadoghq.com/mongo.check_names: '["mongo"]'
    ad.datadoghq.com/mongo.init_configs: '[{}]'
    ad.datadoghq.com/mongo.instances: |
      [
        {
          "hosts": ["%%host%%:%%port%%"], 
          "username": "datadog", 
          "password": "<UNIQUEPASSWORD>", 
          "database": "<DATABASE>"
        }
      ]
spec:
  containers:
    - name: mongo
```

**Annotations v2** (for Datadog Agent v7.36+)

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: mongo
  annotations:
    ad.datadoghq.com/mongo.checks: |
      {
        "mongo": {
          "init_config": {},
          "instances": [
            {
              "hosts": ["%%host%%:%%port%%"], 
              "username": "datadog", 
              "password": "<UNIQUEPASSWORD>", 
              "database": "<DATABASE>"
            }
          ]
        }
      }
spec:
  containers:
    - name: mongo
```

##### Log collection

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes Log Collection][15].

Then, set [Log Integrations][11] as pod annotations. This can also be configured with [a file, a configmap, or a key-value store][16].

**Annotations v1/v2**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: mongo
  annotations:
    ad.datadoghq.com/mongo.logs: '[{"source":"mongodb","service":"<SERVICE_NAME>"}]'
spec:
  containers:
    - name: mongo
```

##### Trace collection

APM for containerized apps is supported on hosts running Agent v6+ but requires extra configuration to begin collecting traces.

Required environment variables on the Agent container:

| Parameter            | Value                                                                      |
| -------------------- | -------------------------------------------------------------------------- |
| `<DD_API_KEY>` | `api_key`                                                                  |
| `<DD_APM_ENABLED>`      | true                                                              |
| `<DD_APM_NON_LOCAL_TRAFFIC>`  | true |

See [Tracing Kubernetes Applications][17] and the [Kubernetes DaemonSet Setup][18] for a complete list of available environment variables and configuration.

Then, [instrument your application container][8] and set `DD_AGENT_HOST` to the name of your Agent container.

<!-- xxz tab xxx -->
<!-- xxx tab "ECS" xxx -->

#### ECS

To configure this check for an Agent running on ECS:

##### Metric collection

Set [Autodiscovery Integrations Templates][9] as Docker labels on your application container:

```json
{
  "containerDefinitions": [{
    "name": "mongo",
    "image": "mongo:latest",
    "dockerLabels": {
      "com.datadoghq.ad.check_names": "[\"mongo\"]",
      "com.datadoghq.ad.init_configs": "[{}]",
      "com.datadoghq.ad.instances": "[{\"hosts\": [\"%%host%%:%%port%%\"], \"username\": \"datadog\", \"password\": \"<UNIQUEPASSWORD>\", \"database\": \"<DATABASE>\"}]"
    }
  }]
}
```

##### Log collection

_Available for Agent versions >6.0_

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [ECS Log Collection][19].

Then, set [Log Integrations][11] as Docker labels:

```json
{
  "containerDefinitions": [{
    "name": "mongo",
    "image": "mongo:latest",
    "dockerLabels": {
      "com.datadoghq.ad.logs": "[{\"source\":\"mongodb\",\"service\":\"<SERVICE_NAME>\"}]"
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

See [Tracing Docker Applications][12] for a complete list of available environment variables and configuration.

Then, [instrument your application container][8] and set `DD_AGENT_HOST` to the [EC2 private IP address][20].


<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's status subcommand][21] and look for `mongo` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][22] for a list of metrics provided by this check.

See the [MongoDB 3.0 Manual][23] for more detailed descriptions of some of these metrics.

#### Additional metrics

The following metrics are **not** collected by default. Use the `additional_metrics` parameter in your `mongo.d/conf.yaml` file to collect them:

| metric prefix            | what to add to `additional_metrics` to collect it |
| ------------------------ | ------------------------------------------------- |
| mongodb.collection       | collection                                        |
| mongodb.commands         | top                                               |
| mongodb.getmore          | top                                               |
| mongodb.insert           | top                                               |
| mongodb.queries          | top                                               |
| mongodb.readLock         | top                                               |
| mongodb.writeLock        | top                                               |
| mongodb.remove           | top                                               |
| mongodb.total            | top                                               |
| mongodb.update           | top                                               |
| mongodb.writeLock        | top                                               |
| mongodb.tcmalloc         | tcmalloc                                          |
| mongodb.metrics.commands | metrics.commands                                  |

### Events

**Replication state changes**:<br>
This check emits an event each time a Mongo node has a change in its replication state.

### Service Checks

See [service_checks.json][24] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][25].

## Further Reading

Additional helpful documentation, links, and articles:

- [Monitoring MongoDB performance metrics (WiredTiger)][26]
- [Monitoring MongoDB performance metrics (MMAP)][27]

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/mongo/images/mongo_dashboard.png
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.mongodb.com/manual/core/replica-set-arbiter/#authentication
[4]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[5]: https://github.com/DataDog/integrations-core/blob/master/mongo/datadog_checks/mongo/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[7]: https://docs.datadoghq.com/tracing/send_traces/
[8]: https://docs.datadoghq.com/tracing/setup/
[9]: https://docs.datadoghq.com/agent/docker/integrations/?tab=docker
[10]: https://docs.datadoghq.com/agent/docker/log/?tab=containerinstallation#installation
[11]: https://docs.datadoghq.com/agent/docker/log/?tab=containerinstallation#log-integrations
[12]: https://docs.datadoghq.com/agent/docker/apm/?tab=linux
[13]: https://docs.datadoghq.com/agent/kubernetes/integrations/?tab=kubernetes
[14]: https://docs.datadoghq.com/agent/kubernetes/integrations/?tab=kubernetes#configuration
[15]: https://docs.datadoghq.com/agent/kubernetes/log/?tab=containerinstallation#setup
[16]: https://docs.datadoghq.com/agent/kubernetes/log/?tab=daemonset#configuration
[17]: https://docs.datadoghq.com/agent/kubernetes/apm/?tab=java
[18]: https://docs.datadoghq.com/agent/kubernetes/daemonset_setup/?tab=k8sfile#apm-and-distributed-tracing
[19]: https://docs.datadoghq.com/agent/amazon_ecs/logs/?tab=linux
[20]: https://docs.datadoghq.com/agent/amazon_ecs/apm/?tab=ec2metadataendpoint#setup
[21]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[22]: https://github.com/DataDog/integrations-core/blob/master/mongo/metadata.csv
[23]: https://docs.mongodb.org/manual/reference/command/dbStats
[24]: https://github.com/DataDog/integrations-core/blob/master/mongo/assets/service_checks.json
[25]: https://docs.datadoghq.com/help/
[26]: https://www.datadoghq.com/blog/monitoring-mongodb-performance-metrics-wiredtiger
[27]: https://www.datadoghq.com/blog/monitoring-mongodb-performance-metrics-mmap
