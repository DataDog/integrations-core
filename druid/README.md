# Agent Check: druid

(TBD Add Druid Dashboard Image here)

## Overview

The Datadog Agent collects many metrics from _Druid_ via DogStatsD. These metrics are Druid are related to queries, ingestion, and coordination:

* Query Metrics
* SQL Metrics
* Coordination
* General Health
* Sys

And many more. See details [here](https://druid.apache.org/docs/latest/operations/metrics.html).

I addition to metrics, the Datadog Agent also sends a service check for Druid health.

## Setup

### Installation

The druid check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

#### Step 1: Configure Druid to collect service checks

1. Edit the `druid.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your druid service checks. See the [sample druid.d/conf.yaml][2] for all available configuration options.

2. [Restart the Agent][3].

#### Step 2: Connect Druid to DogStatsD (included in the Datadog Agent) by using the extension `statsd-emitter` to collect metrics

1) Install Druid extension [`statsd-emitter`](https://druid.apache.org/docs/latest/development/extensions-contrib/statsd.html) 

```
$ java \
  -cp "lib/*" \
  -Ddruid.extensions.directory="./extensions" \
  -Ddruid.extensions.hadoopDependenciesDir="hadoop-dependencies" \
  org.apache.druid.cli.Main tools pull-deps \
  --no-default-hadoop \
  -c "org.apache.druid.extensions.contrib:statsd-emitter:0.15.0-incubating"
```

More info about this step can be found on the [official guide for loading Druid extensions](https://druid.apache.org/docs/latest/operations/including-extensions.html)

2) Update Druid java properties

Update/Add following configs to your druid properties.
```
# Add `statsd-emitter` to the extensions list to be loaded 
druid.extensions.loadList=[..., "statsd-emitter"]

# By default druid emission period is 1 minute (PT1M).
# We recommmend using 15 seconds instead as follow:
druid.monitoring.emissionPeriod=PT15S

# Use `statsd-emitter` extension as metric emitter
druid.emitter=statsd

# Configure `statsd-emitter` endpoint
druid.emitter.statsd.hostname=127.0.0.1
druid.emitter.statsd.port:8125

# Configure `statsd-emitter` to use dogstatsd format 
druid.emitter.statsd.dogstatsd=true
druid.emitter.statsd.dogstatsdServiceAsTag=true
```

Important: `druid.emitter.statsd.dogstatsd` and `druid.emitter.statsd.dogstatsdServiceAsTag` must be set to `true`, otherwise tags might not be reported correctly to Datadog.

Restart Druid to start sending more Druid metrics to DogStatsD (included in the Datadog Agent).


#### Draft notes

- For metrics, Druid is emitting metrics once per minute (configurable).

#### Integration Service Checks

Use the default configuration of your druid.d/conf.yaml file to activate the collection of your Druid service checks. See the sample [druid.d/conf.yaml][10] for all available configuration options.

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

## Data Collected

### Metrics

See [metadata.csv][9] for a list of metrics provided by this check.

### Service Checks

**zookeeper.ruok**:<br>
Sends `ruok` to the monitored node. Returns `OK` with an `imok` response, `WARN` in the case of a different response and `CRITICAL` if no response is received..

**zookeeper.mode**:<br>
The Agent submits this service check if `expected_mode` is configured in `zk.yaml`. The check returns `OK` when Zookeeper's actual mode matches `expected_mode`, otherwise returns `CRITICAL`.


### Events

The Druid check does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][5].

[1]: https://Link-to-Dashboard-image
[1]: **LINK_TO_INTEGRATION_SITE**
[2]: https://github.com/DataDog/integrations-core/blob/master/druid/datadog_checks/druid/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[5]: https://docs.datadoghq.com/help
[9]: https://github.com/DataDog/integrations-core/blob/master/druid/metadata.csv
[10]: https://github.com/DataDog/integrations-core/blob/master/presto/datadog_checks/presto/data/conf.yaml.example