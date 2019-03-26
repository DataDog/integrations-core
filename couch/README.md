# CouchDB Integration

![CouchDB dashboard][1]

## Overview

Capture CouchDB data in Datadog to:

* Visualize key CouchDB metrics.
* Correlate CouchDB performance with the rest of your applications.

For performance reasons, the CouchDB version you're using is cached, so you cannot monitor CouchDB instances with different versions with the same agent instance.

## Setup
### Installation

The CouchDB check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your CouchDB servers.

### Configuration

#### Metric Collection

1. Edit the `couch.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][3] to start collecting your CouchDB performance data. See the [sample couch.d/conf.yaml][4] for all available configuration options.

2. Add this configuration block to your `couch.d/conf.yaml` file to start gathering your [CouchDB Metrics](#metrics):

      ```yaml
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

3. [Restart the Agent][5] to begin sending CouchDB metrics to Datadog.

#### Log Collection

**Available for Agent >6.0**

1. Collecting logs is disabled by default in the Datadog Agent, you need to enable it in `datadog.yaml`:

    ```yaml
    logs_enabled: true
    ```

2. Add this configuration block to your `couch.d/conf.yaml` file to start collecting your CouchDB Logs:

    ```yaml
      logs:
          - type: file
            path: /var/log/couchdb/couch.log
            source: couchdb
            sourcecategory: database
            service: couch
    ```

    Change the `path` and `service` parameter values and configure them for your environment. See the [sample couch.d/conf.yaml][4] for all available configuration options.

3. [Restart the Agent][5].

### Validation

[Run the Agent's `status` subcommand][6] and look for `couch` under the Checks section.

## Data Collected
### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The Couch check does not include any events.

### Service Checks

`couchdb.can_connect`: Returns `Critical` if the Agent cannot connect to CouchDB to collect metrics.

## Troubleshooting
Need help? Contact [Datadog support][8].

## Further Reading

* [Monitoring CouchDB performance with Datadog][9]


[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/couch/images/couchdb_dashboard.png
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/?tab=agentv6#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/couch/datadog_checks/couch/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/couch/metadata.csv
[8]: https://docs.datadoghq.com/help
[9]: https://www.datadoghq.com/blog/monitoring-couchdb-with-datadog
