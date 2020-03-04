# CouchDB Integration

![CouchDB dashboard][1]

## Overview

Capture CouchDB data in Datadog to:

- Visualize key CouchDB metrics.
- Correlate CouchDB performance with the rest of your applications.

For performance reasons, the CouchDB version you're using is cached, so you cannot monitor CouchDB instances with different versions with the same agent instance.

## Setup

### Installation

The CouchDB check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your CouchDB servers.

### Configuration

#### Host

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

##### Metric Collection

1. Edit the `couch.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][3] to start collecting your CouchDB performance data. See the [sample couch.d/conf.yaml][4] for all available configuration options:

   ```yaml
   init_config:

   instances:
     ## @param server - string - required
     ## The Couch server's url.
     #
     - server: http://localhost:5984
   ```

    **Note**: provide a `db_whitelist` and `db_blacklist` to control which databases the Agent should and should not collect metrics from.

2. [Restart the Agent][5].

##### Log collection

_Available for Agent versions >6.0_

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

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][6] for guidance on applying the parameters below.

##### Metric collection

| Parameter            | Value                                |
| -------------------- | ------------------------------------ |
| `<INTEGRATION_NAME>` | `couch`                              |
| `<INIT_CONFIG>`      | blank or `{}`                        |
| `<INSTANCE_CONFIG>`  | `{"server": "http://%%host%%:5984"}` |

##### Log collection

_Available for Agent versions >6.0_

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Docker log collection][7].

| Parameter      | Value                                                |
| -------------- | ---------------------------------------------------- |
| `<LOG_CONFIG>` | `{"source": "couchdb", "service": "<SERVICE_NAME>"}` |

### Validation

[Run the Agent's status subcommand][8] and look for `couch` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][9] for a list of metrics provided by this integration.

### Events

The Couch check does not include any events.

### Service Checks

**couchdb.can_connect**:<br>
Returns `Critical` if the Agent cannot connect to CouchDB to collect metrics, otherwise returns `OK`.

## Troubleshooting

Need help? Contact [Datadog support][10].

## Further Reading

- [Monitoring CouchDB performance with Datadog][11]

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/couch/images/couchdb_dashboard.png
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/couch/datadog_checks/couch/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[7]: https://docs.datadoghq.com/agent/docker/log/
[8]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[9]: https://github.com/DataDog/integrations-core/blob/master/couch/metadata.csv
[10]: https://docs.datadoghq.com/help
[11]: https://www.datadoghq.com/blog/monitoring-couchdb-with-datadog
