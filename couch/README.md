# CouchDB Integration
{{< img src="integrations/couchdb/couchdb_graph.png" alt="CouchDb Graph" responsive="true" popup="true">}}
## Overview

Capture CouchDB data in Datadog to:

* Visualize key CouchDB metrics.
* Correlate CouchDB performance with the rest of your applications.

For performance reasons, the CouchDB version you're using is cached, so you cannot monitor CouchDB instances with different versions with the same agent instance.

## Setup
### Installation

The CouchDB check is packaged with the Agent, so simply [install the Agent][1] on your CouchDB servers.

### Configuration

Create a file `couch.yaml` in the Agent's `conf.d` directory. See the [sample  couch.yaml][2] for all available configuration options:

```
init_config:

instances:
  - server: http://localhost:5984 # or wherever your CouchDB is listening
  #user: <your_username>
  #password: <your_password>
  #name: <A node's Erlang name> # Only for CouchDB 2.x
  #max_nodes_per_check: If no name is specified, the agent will scan all nodes up. As that may be very long, you can limit how many to collect per check. Default: 20
  #max_dbs_per_check. Maximum number of databases to report on. Default: 50
  #tags: A list of tags applied to all metrics collected. Tags may be simple strings or key-value pairs. Default: []
```

Optionally, provide a `db_whitelist` and `db_blacklist` to control which databases the Agent should and should not collect metrics from.

[Restart the Agent][3] to begin sending CouchDB metrics to Datadog.

### Validation

[Run the Agent's `status` subcommand][4] and look for `couch` under the Checks section.

## Data Collected
### Metrics

See [metadata.csv][5] for a list of metrics provided by this integration.

### Events

The Couch check does not include any event at this time.

### Service Checks

`couchdb.can_connect`: Returns `Critical` if the Agent cannot connect to CouchDB to collect metrics.

## Troubleshooting
Need help? Contact [Datadog Support][6].

## Further Reading

* [Monitoring CouchDB performance with Datadog][7]


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/couch/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/couch/metadata.csv
[6]: http://docs.datadoghq.com/help/
[7]: https://www.datadoghq.com/blog/monitoring-couchdb-with-datadog/
