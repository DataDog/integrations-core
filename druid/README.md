# Agent Check: druid

## Overview

The Datadog Agent collects many metrics from _Druid_ via DogStatsD. Those Druid metrics are related to queries, ingestion, and coordination:

* Query Metrics
* SQL Metrics
* Coordination
* General Health
* Sys

And many more. See details [here][1].

I addition to metrics, the Datadog Agent also sends a service check for Druid health.

## Setup

### Prerequisite

Druid 0.16 or above is required for this integration to work properly.

### Installation

The druid check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

#### Step 1: Configure Druid to collect service checks

1. Edit the `druid.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your druid service checks. See the [sample druid.d/conf.yaml][3] for all available configuration options.

2. [Restart the Agent][4].

#### Step 2: Connect Druid to DogStatsD (included in the Datadog Agent) by using the extension `statsd-emitter` to collect metrics

1) Install Druid extension [`statsd-emitter`][5] 

```
$ java \
  -cp "lib/*" \
  -Ddruid.extensions.directory="./extensions" \
  -Ddruid.extensions.hadoopDependenciesDir="hadoop-dependencies" \
  org.apache.druid.cli.Main tools pull-deps \
  --no-default-hadoop \
  -c "org.apache.druid.extensions.contrib:statsd-emitter:0.15.0-incubating"
```

More info about this step can be found on the [official guide for loading Druid extensions][6]

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

#### Integration Service Checks

Use the default configuration of your `druid.d/conf.yaml` file to activate the collection of your Druid service checks. See the sample [druid.d/conf.yaml][3] for all available configuration options.

### Validation

[Run the Agent's status subcommand][7] and look for `druid` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][8] for a list of metrics provided by this check.

### Service Checks

**druid.process.can_connect**:

Returns `CRITICAL` if the check cannot connect to Druid process. Returns `OK` otherwise.

**druid.process.health**:

Returns `CRITICAL` if Druid process is not healthy. Returns `OK` otherwise.


### Events

The Druid check does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][9].

[1]: https://druid.apache.org/docs/latest/operations/metrics.html
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://github.com/DataDog/integrations-core/blob/master/druid/datadog_checks/druid/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[5]: https://druid.apache.org/docs/latest/development/extensions-contrib/statsd.html
[6]: https://druid.apache.org/docs/latest/operations/including-extensions.html
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/druid/metadata.csv
[9]: https://docs.datadoghq.com/help
