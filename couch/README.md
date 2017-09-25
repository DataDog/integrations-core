# CouchDB Integration

## Overview

Capture CouchDB data in Datadog to:

* Visualize key CouchDB metrics.
* Correlate CouchDB performance with the rest of your applications.

## Setup
### Installation

The CouchDB check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your CouchDB servers.

### Configuration

Create a file `couch.yaml` in the Agent's `conf.d` directory:

```
init_config:

instances:
  - server: http://localhost:5984 # or wherever your CouchDB is listening
  #user: <your_username>
  #password: <your_password>
  #name: <A node's Erlang name> # Only for CouchDB 2.x
  #max_nodes_per_check: If no name is specified, the agent will scan all nodes up. As that may be very long, you can limit how many to collect per check. Default: 20
  #max_dbs_per_check. Maximum number of databases to report on. Default: 50
```

Optionally, provide a `db_whitelist` and `db_blacklist` to control which databases the Agent should and should not collect metrics from.

Restart the Agent to begin sending CouchDB metrics to Datadog.

### Validation

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

## Data Collected
### Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/couch/metadata.csv) for a list of metrics provided by this integration.

### Events

The Couch check does not include any event at this time.

### Service Checks

`couchdb.can_connect`: Returns `Critical` if the Agent cannot connect to CouchDB to collect metrics.

### Caveats

For performance reasons, the CouchDB version you're using is cached, so you cannot monitor CouchDB instances with different versions with the same agent instance.

## Troubleshooting

If you have any questions about Datadog or a use case our [Docs](https://docs.datadoghq.com/) didn’t mention, we’d love to help! Here’s how you can reach out to us:

### Visit the Knowledge Base

Learn more about what you can do in Datadog on the [Support Knowledge Base](https://datadog.zendesk.com/agent/).

### Web Support

Messages in the [event stream](https://app.datadoghq.com/event/stream) containing **@support-datadog** will reach our Support Team. This is a convenient channel for referencing graph snapshots or a particular event. In addition, we have a livechat service available during the day (EST) from any page within the app.

### By Email

You can also contact our Support Team via email at [support@datadoghq.com](mailto:support@datadoghq.com).

### Over Slack

Reach out to our team and other Datadog users on [Slack](http://chat.datadoghq.com/).

## Further Reading
To get a better idea of how (or why) to integrate your CouchDB cluster with Datadog, check out our [blog post](https://www.datadoghq.com/blog/monitoring-couchdb-with-datadog/) about it.
