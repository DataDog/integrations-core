# MongoDB check

## Overview

Connect MongoDB to Datadog in order to:

* Visualize key MongoDB metrics.
* Correlate MongoDB performance with the rest of your applications.

## Setup
### Installation

The MongoDB check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your MongoDB masters. If you need the newest version of the check, install the `dd-check-mongo` package.

### Configuration
#### Prepare MongoDB

In a Mongo shell, create a read-only user for the Datadog Agent in the `admin` database:

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

#### Connect the Agent

Create a file `mongodb.yaml` in the Agent's `conf.d` directory:

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



[Restart the Agent](https://help.datadoghq.com/hc/en-us/articles/203764515-Start-Stop-Restart-the-Datadog-Agent) to start sending MongoDB metrics to Datadog.

### Validation

Run the Agent's `info` subcommand and look for `mongo` under the Checks section:

```
  Checks
  ======
    [...]

    mongo
    -------
      - instance #0 [OK]
      - Collected 26 metrics, 1 event & 1 service check

    [...]
```

## Compatibility

The mongo check is compatible with all major platforms.

## Data Collected
### Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/mongo/metadata.csv) for a list of metrics provided by this check.

See the [MongoDB 3.0 Manual](https://docs.mongodb.org/manual/reference/command/dbStats/) for more detailed descriptions of some of these metrics.

**NOTE**: The following metrics are NOT collected by default:

|||
|---|---|
|metric prefix|what to add to `additional_metrics` to collect it|
|mongodb.collection|collection|
|mongodb.commands|top|
|mongodb.getmore|top|
|mongodb.insert|top|
|mongodb.queries|top|
|mongodb.readLock|top|
|mongodb.writeLock|top|
|mongodb.remove|top|
|mongodb.total|top|
|mongodb.update|top|
|mongodb.writeLock|top|
|mongodb.tcmalloc|tcmalloc|
|mongodb.metrics.commands|metrics.commands|

### Events

**Replication state changes**:

This check emits an event each time a Mongo node has a change in its replication state.

### Service Checks

`mongodb.can_connect`:

Returns CRITICAL if the Agent cannot connect to MongoDB to collect metrics, otherwise OK.

## Troubleshooting
Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading
Read our series of blog posts about collecting metrics from MongoDB with Datadog:

* [Start here](https://www.datadoghq.com/blog/monitoring-mongodb-performance-metrics-wiredtiger/) if you're using the WiredTiger storage engine.
* [Start here](https://www.datadoghq.com/blog/monitoring-mongodb-performance-metrics-mmap/) if you're using MMAPv1 storage engine.
