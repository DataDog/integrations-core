# Agent Check: druid

(TBD Add Druid Dashboard Image here)

## Overview

The Datadog Agent collects many metrics from Druid nodes, including those for:

* Service health - for a given service, how many of its nodes are up, passing, warning, critical? (TBD example from Consul)
* Node health - for a given node, how many of its services are up, passing, warning, critical? (TBD example from Consul)

_Druid_ can provide further metrics via DogStatsD. These metrics are Druid are related to queries, ingestion, and coordination:

* Query Metrics
* SQL Metrics
* Coordination
* General Health
* Sys

And many more. See details [here](https://druid.apache.org/docs/latest/operations/metrics.html).

Finally, in addition to metrics, the Datadog Agent also sends a service check for (TBD), and an event (TBD)

## Setup

### Installation

The druid check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `druid.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your druid performance data. See the [sample druid.d/conf.yaml][2] for all available configuration options.

2. [Restart the Agent][3].

(CONFIG TBD)

#### Connect Druid to DogStatsD by using the extension `statsd-emitter`

1) Install `statsd-emitter` extension


```
$ java \
  -cp "lib/*" \
  -Ddruid.extensions.directory="./extensions" \
  -Ddruid.extensions.hadoopDependenciesDir="hadoop-dependencies" \
  org.apache.druid.cli.Main tools pull-deps \
  --no-default-hadoop \
  -c "org.apache.druid.extensions.contrib:statsd-emitter:0.15.0-incubating"
```

2) Update Druid config

```
Update this config:
druid.emitter=statsd
Add those configs
druid.emitter.statsd.hostname=127.0.0.1
druid.emitter.statsd.port:8125
druid.emitter.statsd.dogstatsd=true
```

More info: https://druid.apache.org/docs/latest/development/extensions-contrib/statsd.html

Restart Druid to start sending more Druid metrics to DogStatsD.



#### Draft notes

- For metrics, Druid is emitting metrics once per minute (configurable).

#### Log Collection

**Available for Agent >6.0**

1. Collecting logs is disabled by default in the Datadog Agent, enable it in `datadog.yaml` with:

    ```yaml
    logs_enabled: true
    ```

2. Add this configuration block to your `druid.yaml` file to start collecting your Druid Logs:

    ```yaml
      logs:
          - type: file
            path: (TBD)
            source: druid
            service: myservice
    ```
    Change the `path` and `service` parameter values and configure them for your environment.
    See the [sample druid.d/conf.yaml][4] for all available configuration options.

3. [Restart the Agent][5].

**Learn more about log collection [in the log documentation][6]**


### Validation

[Run the Agent's status subcommand][4] and look for `druid` under the Checks section.

#### Integration Metrics

(TBD Validating integration pulling data from Druid)

#### Druid to DogStatsD

(TBD Validating Dogstatsd integration)

## Data Collected

### Metrics

(TBD)

### Service Checks

(TBD)

### Events

(TBD)

## Troubleshooting

Need help? Contact [Datadog support][5].

[1]: https://Link-to-Dashboard-image
[1]: **LINK_TO_INTEGRATION_SITE**
[2]: https://github.com/DataDog/integrations-core/blob/master/druid/datadog_checks/druid/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[5]: https://docs.datadoghq.com/help
