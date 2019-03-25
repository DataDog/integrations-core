# MongoDB check

![MongoDB Dashboard][1]

## Overview

Connect MongoDB to Datadog in order to:

* Visualize key MongoDB metrics.
* Correlate MongoDB performance with the rest of your applications.

## Setup
### Installation

The MongoDB check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your MongoDB masters.

### Configuration

Edit the `mongo.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][3] to start collecting your MongoDB [metrics](#metric-collection) and [logs](#log-collection).  See the [sample mongo.yaml][4] for all available configuration options.

#### Prepare MongoDB

In a mongo shell, create a read-only user for the Datadog Agent in the `admin` database:

```
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

#### Metric Collection

* Add this configuration block to your `mongo.d/conf.yaml` file to start gathering your [MongoDB Metrics](#metrics). See the [sample mongo.d/conf.yaml][4] for all available configuration options:

  ```
  init_config:
  instances:
    - server: mongodb://datadog:<UNIQUEPASSWORD>@localhost:27017/admin
      additional_metrics:
        - collection       # collect metrics for each collection
        - metrics.commands
        - tcmalloc
        - top
  ```
  See the [sample mongo.yaml][4] for all available configuration options

* [Restart the Agent][5] to start sending MongoDB metrics to Datadog.

#### Log Collection

**Available for Agent >6.0**

* Collecting logs is disabled by default in the Datadog Agent, you need to enable it in `datadog.yaml`:

  ```
  logs_enabled: true
  ```

* Add this configuration block to your `mongo.d/conf.yaml` file to start collecting your MongoDB Logs:

  ```
  logs:
      - type: file
        path: /var/log/mongodb/mongodb.log
        service: mongo
        source: mongodb
  ```
  Change the `service` and `path` parameter values and configure them for your environment.
  See the [sample mongo.yaml][4] for all available configuration options

* [Restart the Agent][5].

**Learn more about log collection [in the log documentation][6]**

### Validation

[Run the Agent's `status` subcommand][7] and look for `mongo` under the Checks section.

## Data Collected
### Metrics

See [metadata.csv][8] for a list of metrics provided by this check.

See the [MongoDB 3.0 Manual][9] for more detailed descriptions of some of these metrics.

**NOTE**: The following metrics are NOT collected by default:

|                          |                                                   |
| ---                      | ---                                               |
| metric prefix            | what to add to `additional_metrics` to collect it |
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

**Replication state changes**:

This check emits an event each time a Mongo node has a change in its replication state.

### Service Checks

`mongodb.can_connect`:

Returns CRITICAL if the Agent cannot connect to MongoDB to collect metrics, otherwise OK.

## Troubleshooting
Need help? Contact [Datadog support][10].

## Further Reading
Read our series of blog posts about collecting metrics from MongoDB with Datadog:

* [Start here][11] if you're using the WiredTiger storage engine.
* [Start here][12] if you're using MMAPv1 storage engine.


[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/mongo/images/mongo_dashboard.png
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/?tab=agentv6#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/mongo/datadog_checks/mongo/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/logs
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/mongo/metadata.csv
[9]: https://docs.mongodb.org/manual/reference/command/dbStats
[10]: https://docs.datadoghq.com/help
[11]: https://www.datadoghq.com/blog/monitoring-mongodb-performance-metrics-wiredtiger
[12]: https://www.datadoghq.com/blog/monitoring-mongodb-performance-metrics-mmap
