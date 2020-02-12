# MongoDB check

![MongoDB Dashboard][1]

## Overview

Connect MongoDB to Datadog in order to:

- Visualize key MongoDB metrics.
- Correlate MongoDB performance with the rest of your applications.

You can also create your own metrics using custom `find`, `count` and `aggregate` queries.

**Note**: MongoDB v2.6+ is required for this integration.

## Setup

### Installation

The MongoDB check is included in the [Datadog Agent][2] package. No additional installation is necessary.

### Configuration

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

#### Host

##### Prepare MongoDB

In a Mongo shell, create a read-only user for the Datadog Agent in the `admin` database:

```shell
# Authenticate as the admin user.
use admin
db.auth("admin", "<YOUR_MONGODB_ADMIN_PASSWORD>")

# On MongoDB 2.x, use the addUser command.
db.addUser("datadog", "<UNIQUEPASSWORD>", true)

# On MongoDB 3.x or higher, use the createUser command.
db.createUser({
  "user":"datadog",
  "pwd": "<UNIQUEPASSWORD>",
  "roles" : [
    {role: 'read', db: 'admin' },
    {role: 'clusterMonitor', db: 'admin'},
    {role: 'read', db: 'local' }
  ]
})
```

##### Metric collection

1. Edit the `mongo.d/conf.yaml` file in the `conf.d` folder at the root of your [Agent's configuration directory][3]. See the [sample mongo.d/conf.yaml][4] for all available configuration options.

   ```yaml
   init_config:
   instances:
     ## @param server - string - required
     ## Specify the MongoDB URI, with database to use for reporting (defaults to "admin")
     ## E.g. mongodb://datadog:LnCbkX4uhpuLHSUrcayEoAZA@localhost:27016/admin
     #
     - server: "mongodb://datadog:<UNIQUEPASSWORD>@<HOST>:<PORT>/<DB_NAME>"

       ## @param replica_check - boolean - required - default: true
       ## Whether or not to read from available replicas.
       ## Disable this if any replicas are inaccessible to the agent.
       #
       replica_check: true

       ## @param additional_metrics - list of strings - optional
       ## By default, the check collects a sample of metrics from MongoDB.
       ## This  parameter instructs the check to collect additional metrics on specific topics.
       ## Available options are:
       ##   * `metrics.commands` - Use of database commands
       ##   * `tcmalloc` -  TCMalloc memory allocator
       ##   * `top` - Usage statistics for each collection
       ##   * `collection` - Metrics of the specified collections
       #
       additional_metrics:
         - metrics.commands
         - tcmalloc
         - top
         - collection
   ```

2. [Restart the Agent][5].

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

    Change the `service` and `path` parameter values and configure them for your environment. See the [sample mongo.yaml][4] for all available configuration options

3. [Restart the Agent][5].

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][6] for guidance on applying the parameters below.

##### Metric collection

| Parameter            | Value                                                                                                                                                                           |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `<INTEGRATION_NAME>` | `mongo`                                                                                                                                                                         |
| `<INIT_CONFIG>`      | blank or `{}`                                                                                                                                                                   |
| `<INSTANCE_CONFIG>`  | `{"server": "mongodb://datadog:<UNIQUEPASSWORD>@%%host%%:%%port%%/<DB_NAME>", "replica_check": true, "additional_metrics": ["metrics.commands","tcmalloc","top","collection"]}` |

##### Log collection

_Available for Agent versions >6.0_

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Docker log collection][7].

| Parameter      | Value                                       |
| -------------- | ------------------------------------------- |
| `<LOG_CONFIG>` | `{"source": "mongodb", "service": "mongo"}` |

### Validation

[Run the Agent's status subcommand][8] and look for `mongo` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][9] for a list of metrics provided by this check.

See the [MongoDB 3.0 Manual][10] for more detailed descriptions of some of these metrics.

**NOTE**: The following metrics are NOT collected by default, use the `additional_metrics` parameter in your `mongo.d/conf.yaml` file to collect them:

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

**mongodb.can_connect**:<br>
Returns `CRITICAL` if the Agent cannot connect to MongoDB to collect metrics, otherwise returns `OK`.

## Troubleshooting

Need help? Contact [Datadog support][11].

## Further Reading

Read our series of blog posts about collecting metrics from MongoDB with Datadog:

- [Monitoring MongoDB performance metrics (WiredTiger)][12]
- [Monitoring MongoDB performance metrics (MMAP)][13]

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/mongo/images/mongo_dashboard.png
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/mongo/datadog_checks/mongo/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[7]: https://docs.datadoghq.com/agent/docker/log/
[8]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[9]: https://github.com/DataDog/integrations-core/blob/master/mongo/metadata.csv
[10]: https://docs.mongodb.org/manual/reference/command/dbStats
[11]: https://docs.datadoghq.com/help
[12]: https://www.datadoghq.com/blog/monitoring-mongodb-performance-metrics-wiredtiger
[13]: https://www.datadoghq.com/blog/monitoring-mongodb-performance-metrics-mmap
