# CouchDB Integration

# Overview

Capture CouchDB data in Datadog to:

* Visualize key CouchDB metrics.
* Correlate CouchDB performance with the rest of your applications.

# Installation

The CouchDB check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your CouchDB servers.

# Configuration

Create a file `couch.yaml` in the Agent's `conf.d` directory:

```
init_config:

instances:
  - server: http://localhost:5984 # or wherever your CouchDB is listening
  #user: <your_username>
  #password: <your_password>
```

Optionally, provide a `db_whitelist` and `db_blacklist` to control which databases the Agent should and should not collect metrics from.

If using couch 2.0, add `couch_2` to get stats from each node.

Restart the Agent to begin sending CouchDB metrics to Datadog.

# Validation

Run the Agent's `info` subcommand and look for `couch` under the Checks section:

```
  Checks
  ======
    [...]

    couch
    -------
      - instance #0 [OK]
      - Collected 26 metrics, 0 events & 1 service check

    [...]
```

# Troubleshooting

# Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/couch/metadata.csv) for a list of metrics provided by this integration.

# Events

# Service Checks

`couchdb.can_connect`:

Returns `Critical` if the Agent cannot connect to CouchDB to collect metrics.

# Further Reading

To get a better idea of how (or why) to integrate your CouchDB cluster with Datadog, check out our [blog post](https://www.datadoghq.com/blog/monitoring-couchdb-with-datadog/) about it.
