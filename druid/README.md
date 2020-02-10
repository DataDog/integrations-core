# Agent Check: Druid

![Druid Dashboard][1]

## Overview

The Datadog Agent collects metrics from Druid using [DogStatsD][2]. DogStatsD collects metrics on Druid queries, ingestion, and coordination data. For more information, see the [Druid metrics documentation][3].

In addition to collecting metrics, the Agent also sends a Service Check related to Druid's health.

## Setup

### Prerequisite

Druid 0.16 or above is required for this integration to work properly.

### Installation

Both steps below are needed for Druid integration to work properly. Before you begin, you should [install the Datadog Agent][4].

#### Step 1: Configure Druid to collect health metrics and service checks

Configure the Druid check included in the [Datadog Agent][5] package to collect health metrics and service checks.

1. Edit the `druid.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your druid service checks. See the [sample druid.d/conf.yaml][6] for all available configuration options.
2. [Restart the Agent][7].

#### Step 2: Connect Druid to DogStatsD (included in the Datadog Agent) by using the extension `statsd-emitter` to collect metrics

Step to configure `statsd-emitter` extension to collect the majority of [Druid metrics][3].

1. Install the Druid extension [`statsd-emitter`][8].

   ```shell
   $ java \
     -cp "lib/*" \
     -Ddruid.extensions.directory="./extensions" \
     -Ddruid.extensions.hadoopDependenciesDir="hadoop-dependencies" \
     org.apache.druid.cli.Main tools pull-deps \
     --no-default-hadoop \
     -c "org.apache.druid.extensions.contrib:statsd-emitter:0.15.0-incubating"
   ```

    More info about this step can be found on the [official guide for loading Druid extensions][9]

2. Update Druid java properties by adding the following configs:

   ```conf
   # Add `statsd-emitter` to the extensions list to be loaded
   druid.extensions.loadList=[..., "statsd-emitter"]

   # By default druid emission period is 1 minute (PT1M).
   # We recommend using 15 seconds instead:
   druid.monitoring.emissionPeriod=PT15S

   # Use `statsd-emitter` extension as metric emitter
   druid.emitter=statsd

   # Configure `statsd-emitter` endpoint
   druid.emitter.statsd.hostname=127.0.0.1
   druid.emitter.statsd.port:8125

   # Configure `statsd-emitter` to use dogstatsd format. Must be set to true, otherwise tags are not reported correctly to Datadog.
   druid.emitter.statsd.dogstatsd=true
   druid.emitter.statsd.dogstatsdServiceAsTag=true
   ```

3. Restart Druid to start sending your Druid metrics to the Agent through DogStatsD.

#### Integration Service Checks

Use the default configuration of your `druid.d/conf.yaml` file to activate the collection of your Druid service checks. See the sample [druid.d/conf.yaml][6] for all available configuration options.

#### Log collection

_Available for Agent versions >6.0_

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your datadog.yaml file:

   ```yaml
   logs_enabled: true
   ```

2. Uncomment and edit this configuration block at the bottom of your `druid.d/conf.yaml`:

   ```yaml
   logs:
     - type: file
       path: '<PATH_TO_DRUID_DIR>/var/sv/*.log'
       source: druid
       service: '<SERVICE_NAME>'
       log_processing_rules:
         - type: multi_line
           name: new_log_start_with_date
           pattern: \d{4}\-\d{2}\-\d{2}
   ```

    Change the `path` and `service` parameter values and configure them for your environment.

3. [Restart the Agent][7].

### Validation

[Run the Agent's status subcommand][10] and look for `druid` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][11] for a list of metrics provided by this check.

### Service Checks

**druid.process.can_connect**:

Returns `CRITICAL` if the check cannot connect to Druid process. Returns `OK` otherwise.

**druid.process.health**:

Returns `CRITICAL` if Druid process is not healthy. Returns `OK` otherwise.

### Events

The Druid check does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][12].

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/druid/assets/images/druid_dashboard_overview.png
[2]: https://docs.datadoghq.com/developers/dogstatsd/
[3]: https://druid.apache.org/docs/latest/operations/metrics.html
[4]: https://docs.datadoghq.com/agent/
[5]: https://app.datadoghq.com/account/settings#agent
[6]: https://github.com/DataDog/integrations-core/blob/master/druid/datadog_checks/druid/data/conf.yaml.example
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[8]: https://druid.apache.org/docs/latest/development/extensions-contrib/statsd.html
[9]: https://druid.apache.org/docs/latest/operations/including-extensions.html
[10]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[11]: https://github.com/DataDog/integrations-core/blob/master/druid/metadata.csv
[12]: https://docs.datadoghq.com/help
